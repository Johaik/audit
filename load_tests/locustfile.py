import time
import uuid
import random
from locust import HttpUser, task, between
from datetime import datetime, timedelta

class AuditApiUser(HttpUser):
    wait_time = between(0.1, 0.5) # Simulate high throughput
    
    def on_start(self):
        # Pick a tenant for this user session
        self.tenant_id = f"tenant-{random.randint(1, 100)}"
        self.headers = {"X-Tenant-ID": self.tenant_id}
        self.created_events = []

    @task(3)
    def create_event(self):
        """Create a new event"""
        event_id = str(uuid.uuid4())
        payload = {
            "idempotency_key": event_id,
            "occurred_at": datetime.utcnow().isoformat() + "Z",
            "type": random.choice(["user.login", "user.logout", "order.created", "order.paid"]),
            "actor": { 
                "kind": "user", 
                "id": f"user-{random.randint(1, 1000)}" 
            },
            "entities": [
                { "kind": "user", "id": f"u-{random.randint(1, 100)}" },
                { "kind": "order", "id": f"o-{random.randint(1, 100)}" }
            ],
            "payload": {
                "browser": "chrome",
                "ip": "127.0.0.1",
                "amount": random.randint(10, 1000)
            }
        }
        
        with self.client.post("/v1/events", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
                # Store for timeline queries
                if response.json().get("entities"):
                    self.created_events.append(response.json())
            elif response.status_code == 200:
                # Idempotent success (shouldn't happen much with uuid keys but possible in reuse tests)
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code} - {response.text}")

    @task(1)
    def get_timeline(self):
        """Query timeline for an entity"""
        if not self.created_events:
            return
            
        # Pick a random event and query one of its entities
        event = random.choice(self.created_events)
        if not event.get("entities"):
            return
            
        entity = random.choice(event["entities"])
        entity_query = f"{entity['entity_kind']}:{entity['entity_id']}"
        
        with self.client.get(f"/v1/timeline?entity={entity_query}&limit=10", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Timeline failed: {response.status_code} - {response.text}")

    @task(1)
    def create_duplicate_idempotency(self):
        """Test idempotency mechanism by replaying a recent event"""
        if not self.created_events:
            return

        event = random.choice(self.created_events)
        
        # Construct payload matching the original event to ensure hash matches
        # Note: This is tricky in load tests because we need exact same payload.
        # For simplicity, we'll rely on the fact that if we use the same key,
        # we expect 200 OK (if we can reconstruct payload) or 409 (if we change it).
        # Let's try to send a conflict to stress the hash check.
        
        payload = {
            "idempotency_key": event["idempotency_key"], # Reuse key
            "occurred_at": datetime.utcnow().isoformat() + "Z", # New time -> Hash mismatch!
            "type": "retry.attempt",
            "actor": { "kind": "bot", "id": "retry-bot" },
            "entities": [],
            "payload": {}
        }
        
        with self.client.post("/v1/events", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 409:
                response.success() # Expected conflict
            elif response.status_code == 200:
                 response.failure("Should have been 409 conflict")
            else:
                 # It might be 201 if the original event wasn't actually saved (e.g. valid first time seen by this worker)
                 # But we picked from self.created_events, so it should exist.
                 response.failure(f"Idempotency check failed: {response.status_code}")

