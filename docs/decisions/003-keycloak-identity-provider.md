# Keycloak for Identity and Access Management

**Date:** 2025-12-26
**Status:** Accepted

## Context

The Audit Service requires a robust multi-tenant authentication and authorization system. Key requirements include:
1.  **Multi-tenancy:** Securely isolating data between tenants.
2.  **Machine-to-Machine Auth:** Services pushing logs need long-lived or renewable credentials (service accounts).
3.  **Database Integration:** The authentication mechanism must seamlessly integrate with my Postgres Row Level Security (RLS) strategy, which relies on a Tenant ID (`tid`) being present in the request context.
4.  **Standards Compliance:** Using standard protocols (OIDC/OAuth2) to avoid "rolling my own crypto."

## Alternatives Considered

1.  **Custom Implementation (JWTs + Database Tables)**
    *   *Pros:* Full control, lightweight (no extra service to run).
    *   *Cons:* High security risk (encryption, key rotation, token invalidation are hard to get right), significant development effort, maintenance burden.

2.  **SaaS Identity Providers (Auth0, Okta, AWS Cognito)**
    *   *Pros:* Managed service (no operational overhead), high reliability, advanced features.
    *   *Cons:* Cost can scale linearly with active tenants/tokens, potential vendor lock-in, data sovereignty concerns if sensitive metadata is stored.

3.  **Keycloak (Self-Hosted)**
    *   *Pros:* Open Source (Apache 2.0), free to use, full control over data, extensive feature set (OIDC, SAML, Social Auth), mature ecosystem. Supports fine-grained customization like Protocol Mappers.
    *   *Cons:* Operational complexity (JVM-based, resource intensive), requires managing updates and availability.

## Decision

I chose **Keycloak** as my Identity Provider.

## Implementation Details

The implementation follows the **Adapter Pattern** to decouple my application logic from the specific IdP.

1.  **Abstraction (`IdPProvider`):**
    I defined an abstract base class `app.core.auth.idp.IdPProvider` that outlines the contract:
    *   `create_tenant_client`: Provisions a new client for a tenant.
    *   `validate_token`: Verifies JWT signatures and extracts claims.
    *   `get_public_key`: Fetches the public key for local validation.

2.  **Concrete Implementation (`KeycloakProvider`):**
    I use the `python-keycloak` library to interact with the Keycloak Admin API.

3.  **Tenant Provisioning Flow:**
    When a new tenant is created in the system:
    *   A new **Client** is created in Keycloak (Service Account enabled, Standard Flow disabled).
    *   A **Protocol Mapper** (`oidc-hardcoded-claim-mapper`) is explicitly added to this client.
    *   This mapper hardcodes the specific `tenant_id` into a custom claim named `tid` in every access token issued for this client.

4.  **Row Level Security (RLS) Integration:**
    *   Incoming requests bear a JWT.
    *   The API validates the JWT signature using Keycloak's public key.
    *   The `tid` claim is extracted.
    *   This `tid` is passed to the Postgres session (e.g., `SET app.current_tenant = '...'`) to enforce RLS.

## Consequences

*   **Positive:**
    *   **Security:** I rely on a battle-tested OIDC provider rather than custom code.
    *   **Flexibility:** The protocol mapper approach allows me to bind authorization context (Tenant ID) directly to authentication tokens, simplifying the API layer.
    *   **Decoupling:** The `IdPProvider` interface allows me to swap Keycloak for Auth0 or another provider in the future if operational costs become too high, with minimal code changes.

*   **Negative:**
    *   **Infrastructure:** I must maintain a Keycloak container/deployment.
    *   **Performance:** fetching tokens involves a network hop (though validation is local/stateless).
