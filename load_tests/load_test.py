import asyncio
import httpx
import time
import uuid
import random
import json
import os
import sys
from datetime import datetime

# Ensure we can import from local utils
sys.path.append(os.path.dirname(__file__))

try:
    from utils import get_token
except ImportError:
    from load_tests.utils import get_token

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000/v1/events")
NUM_REQUESTS = 1000
CONCURRENCY = 50
EVENT_TYPES = ["user.created", "invoice.paid", "order.shipped", "page.viewed"]

TENANTS_FILE = os.path.join(os.path.dirname(__file__), "tenants.json")

def load_tenants():
    if not os.path.exists(TENANTS_FILE):
        print("Tenants file not found. Please run setup_tenants.py first.")
        return []
    with open(TENANTS_FILE, "r") as f:
        return json.load(f)

async def send_event(client, tenant_config):
    # Get token (synchronously, assuming cached mostly)
    try:
        # Note: get_token is synchronous (uses requests), which blocks the event loop.
        # In a real high-perf async app, we should use an async auth client.
        # For this test script, it's acceptable if cached, but ideally we'd offload to thread.
        token = get_token(tenant_config["client_id"], tenant_config["client_secret"])
    except Exception as e:
        return "AuthError", 0, str(e)

    event_id = str(uuid.uuid4())
    payload = {
        "idempotency_key": f"req-{event_id}",
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "type": random.choice(EVENT_TYPES),
        "actor": { "kind": "user", "id": f"u-{random.randint(1, 100)}" },
        "entities": [
            { "kind": "invoice", "id": f"inv-{random.randint(1000, 9999)}" },
            { "kind": "account", "id": f"acc-{random.randint(1, 50)}" }
        ],
        "trace": { "trace_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()) },
        "payload": { "amount": random.uniform(10.0, 500.0), "currency": "USD" }
    }
    
    start_time = time.time()
    try:
        response = await client.post(
            API_URL, 
            json=payload, 
            headers={"Authorization": f"Bearer {token}"}
        )
        duration = time.time() - start_time
        
        if response.status_code not in (200, 201):
            return response.status_code, duration, response.text
            
        # Optional: Check RLS (if API returns tenant_id)
        data = response.json()
        if data.get("tenant_id") and data.get("tenant_id") != tenant_config["id"]:
             return "RLS_FAIL", duration, f"Got {data.get('tenant_id')} expected {tenant_config['id']}"

        return response.status_code, duration, None
    except Exception as e:
        return "Exception", time.time() - start_time, str(e)

async def worker(queue, client, results, errors, tenants):
    while True:
        try:
            _ = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        
        tenant = random.choice(tenants)
        status, duration, error_detail = await send_event(client, tenant)
        results.append((status, duration))
        if error_detail:
            errors.append((status, error_detail))
        queue.task_done()

async def run_load_test():
    tenants = load_tenants()
    if not tenants:
        return

    queue = asyncio.Queue()
    results = []
    errors = []
    
    for _ in range(NUM_REQUESTS):
        queue.put_nowait(1)
        
    print(f"Starting load test: {NUM_REQUESTS} requests, {CONCURRENCY} concurrency")
    start_total = time.time()
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=CONCURRENCY, max_connections=CONCURRENCY), timeout=30.0) as client:
        workers = [asyncio.create_task(worker(queue, client, results, errors, tenants)) for _ in range(CONCURRENCY)]
        await queue.join()
        for w in workers:
            w.cancel()
            
    total_duration = time.time() - start_total
    
    # Analysis
    success_count = sum(1 for s, _ in results if s == 201 or s == 200)
    failed_count = NUM_REQUESTS - success_count
    avg_latency = sum(d for _, d in results) / len(results) * 1000 if results else 0
    req_per_sec = NUM_REQUESTS / total_duration
    
    print("\n--- Load Test Results ---")
    print(f"Total Time: {total_duration:.2f}s")
    print(f"Requests: {NUM_REQUESTS}")
    print(f"Throughput: {req_per_sec:.2f} req/sec")
    print(f"Success (200/201): {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Avg Latency: {avg_latency:.2f} ms")

    if errors:
        print("\n--- Errors (First 5) ---")
        for i, (status, detail) in enumerate(errors[:5]):
             print(f"{i+1}. Status: {status} | Detail: {detail}")

if __name__ == "__main__":
    try:
        asyncio.run(run_load_test())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
