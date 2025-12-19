import os
import sys
import time
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakConnectionError

# Ensure we can import app
sys.path.append(os.getcwd())
from app.config import settings

def wait_for_keycloak(kcadm, max_retries=30):
    print(f"Connecting to Keycloak at {settings.KEYCLOAK_URL}...")
    for i in range(max_retries):
        try:
            # Try to get server info or just list realms to check connection
            kcadm.get_realms()
            print("Connected to Keycloak.")
            return True
        except Exception:
            print(f"Waiting for Keycloak... ({i+1}/{max_retries})")
            time.sleep(2)
    return False

def init_keycloak():
    # Connect to master realm to manage realms
    try:
        kcadm = KeycloakAdmin(
            server_url=settings.KEYCLOAK_URL,
            username=settings.KEYCLOAK_ADMIN_USER,
            password=settings.KEYCLOAK_ADMIN_PASSWORD,
            realm_name="master",
            verify=True
        )
    except Exception as e:
        print(f"Failed to initialize Keycloak client: {e}")
        return

    if not wait_for_keycloak(kcadm):
        print("Could not connect to Keycloak. Exiting.")
        sys.exit(1)

    # Check if realm exists
    realms = kcadm.get_realms()
    realm_names = [r['realm'] for r in realms]
    
    if settings.KEYCLOAK_REALM not in realm_names:
        print(f"Creating realm: {settings.KEYCLOAK_REALM}")
        kcadm.create_realm(payload={
            "realm": settings.KEYCLOAK_REALM,
            "enabled": True,
            "accessTokenLifespan": 3600
        })
        print("Realm created.")
    else:
        print(f"Realm {settings.KEYCLOAK_REALM} already exists.")

if __name__ == "__main__":
    init_keycloak()

