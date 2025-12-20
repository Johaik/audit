# Future Scaling and Performance Strategies

This document outlines potential strategies and implementation ideas to handle growth, improve performance, and ensure the longevity of the Audit Service.

## 1. Database Scaling: Partitioning
As the volume of audit logs grows, the `events` table will become the primary bottleneck for both writes and reads.

*   **Strategy:** Implement PostgreSQL **Declarative Partitioning** on the `events` and `event_entities` tables.
*   **Partition Key:** `timestamp` (Range Partitioning).
*   **Granularity:** Monthly or Quarterly partitions.
*   **Benefits:**
    *   **Query Performance:** Queries constrained by time ranges (the 90% case) will only scan relevant partitions.
    *   **Maintenance:** "Deleting" old data becomes a constant-time `DROP TABLE` operation on an old partition, rather than a slow `DELETE` that bloats the table.

## 2. Read/Write Splitting
Audit systems typically have a high Write:Read ratio, but read queries (searches) can be complex and resource-intensive.

*   **Strategy:** Configure PostgreSQL with a Primary (Writer) and one or more Read Replicas.
*   **Implementation:**
    *   **Ingestion API:** Connects strictly to the Primary.
    *   **Search/Admin API:** Connects to Read Replicas.
*   **Challenge:** Replication lag.
    *   *Mitigation:* Accept eventual consistency for search queries. Users searching for an event that happened *milliseconds* ago might miss it, which is usually acceptable for audit logs.

## 3. Data Archival (Cold Storage)
Indefinite retention in a transactional database is cost-prohibitive and degrades performance.

*   **Strategy:** Tiered storage lifecycle.
    1.  **Hot (0-1 year):** In Postgres (partitioned).
    2.  **Cold (1+ years):** Offload to Object Storage (S3, GCS) in columnar formats (Parquet/Avro).
*   **Implementation:**
    *   Automated cron job to export "closed" partitions to S3.
    *   Update the Search API to optionally query cold storage (via tools like Amazon Athena or Trino) for "Deep Search" capabilities, accepting higher latency.

## 4. Ingestion Buffering (Async Writes)
Direct HTTP-to-Database writes can cause backpressure on clients during traffic spikes.

*   **Strategy:** Decouple ingestion from storage using a Message Queue.
*   **Flow:** Client -> API -> **Kafka/RabbitMQ** -> Worker -> Database.
*   **Benefits:**
    *   **Smoothing:** Spikes in traffic are absorbed by the queue.
    *   **Batching:** Workers can bulk-insert records (e.g., `COPY` command) which is significantly faster than single-row `INSERT`s.

## 5. Horizontal Application Scaling
*   **Strategy:** The API layer is stateless. It can be scaled horizontally using a Load Balancer (Kubernetes/AWS ALB).
*   **Constraint:** Ensure the `IdPProvider` (Keycloak integration) handles public key caching efficiently across instances to avoid hammering the IdP.

## 6. Tenant-Specific Optimizations
For extremely large tenants ("Whales"):

*   **Strategy:** Dedicated Shards.
*   **Implementation:** If a single tenant dominates traffic, move them to a dedicated database instance while keeping the same API interface. The Router would direct traffic based on `tenant_id` to the correct DB connection pool.

## 7. Hybrid Storage (Postgres + NoSQL)
An alternative architecture considered for handling massive scale, specifically if event payloads become very large.

*   **Strategy:** Store lightweight metadata in PostgreSQL and the heavy JSON payload in a NoSQL store.
*   **Split:**
    *   **Postgres:** `id`, `tenant_id`, `timestamp`, `actor`, `action`, `entities` (for RLS and Indexing).
    *   **NoSQL (e.g., MongoDB, ScyllaDB, DynamoDB):** `event_id`, `full_json_payload`.
*   **Benefits:**
    *   **Postgres Performance:** Keeps the Postgres rows small, reducing I/O and VACUUM overhead (avoiding TOAST table bloat).
    *   **Write Throughput:** NoSQL stores are typically optimized for high-volume ingestion of unstructured data.
*   **Trade-offs:**
    *   **Complexity:** Requires maintaining two distinct storage systems.
    *   **Consistency:** Loss of atomic transactions (ACID) across the two stores. If the NoSQL write fails but Postgres succeeds (or vice versa), the system enters an inconsistent state.

## 8. CQRS with OpenSearch for Advanced Analytics
To support complex analytical queries (e.g., "count events by type per hour") and full-text search without impacting the primary database.

*   **Strategy:** Command Query Responsibility Segregation (CQRS) using the **Transactional Outbox Pattern**.
*   **Components:**
    *   **Write Side (Command):** Postgres (Source of Truth).
    *   **Read Side (Query):** OpenSearch (or Elasticsearch).
*   **Sync Implementation (The Outbox Pattern):**
    1.  **Atomic Write:** When an event is inserted into the `events` table, the application also inserts a record into an `outbox` table *within the same database transaction*.
    2.  **Async Propagation:** A separate process (e.g., Debezium or a custom background worker) polls or tails the `outbox` table.
    3.  **Indexing:** The worker pushes the new events to OpenSearch.
    4.  **Completion:** Once indexed, the `outbox` entry is marked as processed or deleted.
*   **Benefits:**
    *   **Reliability:** Guarantees **at-least-once delivery** to the analytics engine even if the application crashes after writing to the DB.
    *   **Performance:** Decouples the latency of indexing in OpenSearch from the critical path of the API response.
    *   **Capability:** Enables powerful Kibana dashboards and fuzzy search capabilities that Postgres cannot match.
