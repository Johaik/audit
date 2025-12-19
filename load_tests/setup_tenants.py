import requests
import json
import os
import sys

# Add project root to path to import config if needed, or just use hardcoded defaults/env vars
sys.path.append(os.getcwd())

API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key")
NUM_TENANTS = 3
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "tenants.json")

def create_tenant(name):
    url = f"{API_URL}/admin/tenants"
    headers = {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json"
    }
    payload = {"name": name}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to create tenant {name}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.text}")
        return None

def main():
    print(f"Provisioning {NUM_TENANTS} tenants at {API_URL}...")
    
    tenants = []
    for i in range(NUM_TENANTS):
        name = f"load-test-tenant-{i+1}"
        print(f"Creating {name}...")
        tenant_data = create_tenant(name)
        if tenant_data:
            tenants.append(tenant_data)
            print(f"  -> Success: {tenant_data['id']}")
    
    if not tenants:
        print("No tenants created. Exiting.")
        sys.exit(1)
        
    with open(OUTPUT_FILE, "w") as f:
        json.dump(tenants, f, indent=2)
        
    print(f"Successfully saved {len(tenants)} tenants to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

