import json
import os
import random
import uuid
import sys
from datetime import datetime
from locust import HttpUser, task, between, events
from locust.exception import StopUser

# Ensure we can import from local utils
sys.path.append(os.path.dirname(__file__))

try:
    from utils import get_token
except ImportError:
    # If running from root
    from load_tests.utils import get_token

TENANTS_FILE = os.path.join(os.path.dirname(__file__), "tenants.json")

# Load tenants globally
TENANTS = []
if os.path.exists(TENANTS_FILE):
    with open(TENANTS_FILE, "r") as f:
        TENANTS = json.load(f)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    if not TENANTS:
        print("ERROR: No tenants found in tenants.json. Please run 'python load_tests/setup_tenants.py' first.")
        environment.runner.quit()

class AuditApiUser(HttpUser):
    wait_time = between(0.1, 0.5)
    host = "http://localhost:8000"  # Set default host
    
    def on_start(self):
        if not TENANTS:
            raise StopUser()
            
        # Pick a tenant for this user session
        self.tenant_config = random.choice(TENANTS)
        self.tenant_id = self.tenant_config["id"]
        
        # Authenticate
        try:
            self.token = get_token(
                self.tenant_config["client_id"], 
                self.tenant_config["client_secret"]
            )
            self.headers = {"Authorization": f"Bearer {self.token}"}
        except Exception as e:
            print(f"Failed to authenticate tenant {self.tenant_id}: {e}")
            raise StopUser()
            
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
                data = response.json()
                # Verify Tenant ID (RLS check)
                if data.get("tenant_id") != self.tenant_id:
                     response.failure(f"RLS Violation: Returned tenant_id {data.get('tenant_id')} != {self.tenant_id}")
                     return

                response.success()
                if data.get("entities"):
                    self.created_events.append(data)
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code} - {response.text}")

    @task(1)
    def get_timeline(self):
        """Query timeline for an entity"""
        if not self.created_events:
            return
            
        event = random.choice(self.created_events)
        if not event.get("entities"):
            return
            
        # The entities in the response are Pydantic models dumped to dicts
        # The schema uses validation_alias for 'entity_kind' -> 'kind' in request
        # But in response (EventRead), entities is List[EntityRead]
        # EntityRead has: kind = Field(validation_alias="entity_kind")
        # So when serialized, it might be 'kind' or 'entity_kind' depending on configuration
        
        # Let's check what the API returns.
        # Based on app/schemas/common.py:
        # class EntityRead(BaseModel):
        #    kind: str = Field(validation_alias="entity_kind")
        #    id: str = Field(validation_alias="entity_id")
        
        # When serialized by FastAPI/Pydantic, it usually uses the field name ('kind', 'id')
        
        entity = random.choice(event["entities"])
        
        # Helper to get field regardless of alias
        kind = entity.get("kind") or entity.get("entity_kind")
        e_id = entity.get("id") or entity.get("entity_id")
        
        if not kind or not e_id:
             return

        entity_query = f"{kind}:{e_id}"
        
        with self.client.get(f"/v1/timeline?entity={entity_query}&limit=10", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                # Verify RLS: All events must belong to my tenant
                for e in events:
                    if e["tenant_id"] != self.tenant_id:
                        response.failure(f"RLS Violation in Timeline: Found event for tenant {e['tenant_id']}")
                        return
                response.success()
            else:
                response.failure(f"Timeline failed: {response.status_code} - {response.text}")

    @task(1)
    def create_duplicate_idempotency(self):
        """Test idempotency mechanism by replaying a recent event"""
        if not self.created_events:
            return

        event = random.choice(self.created_events)
        
        payload = {
            "idempotency_key": event["idempotency_key"],
            "occurred_at": datetime.utcnow().isoformat() + "Z", # New time -> Hash mismatch!
            "type": "retry.attempt",
            "actor": { "kind": "bot", "id": "retry-bot" },
            "entities": [],
            "payload": {}
        }
        
        with self.client.post("/v1/events", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 409:
                response.success()
            elif response.status_code == 200:
                 response.failure("Should have been 409 conflict")
            else:
                 response.failure(f"Idempotency check failed: {response.status_code}")
