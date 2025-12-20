# 3. Use Keycloak for Identity Management

Date: 2025-12-26

## Status

Accepted

## Context

The service requires robust authentication and authorization mechanisms for both the internal admin API and external client ingestion/query APIs. I need to manage client credentials (service accounts) for microservices that will push logs. Building a secure auth system from scratch is risky and time-consuming.

## Decision

I will use **Keycloak** as the Identity Provider (IdP).

*   **Protocol:** OIDC (OpenID Connect).
*   **Tenant Provisioning:** Each tenant in the Audit Service corresponds to a Keycloak `Client`.
*   **Authentication:** Clients authenticate using the `client_credentials` grant flow to obtain a JWT.
*   **Authorization:** The JWT contains a custom claim (`tid`) representing the Tenant ID, which the Audit API uses to set the RLS context.

## Consequences

*   **Positive:**
    *   **Standard Compliance:** Uses standard OIDC/OAuth2 protocols.
    *   **Feature Rich:** Supports token rotation, revocation, various grant types, and fine-grained permissions out of the box.
    *   **Offloading Security:** Shifts the burden of credential storage and token management to a dedicated, battle-tested solution.
*   **Negative:**
    *   **Operational Overhead:** Requires running and maintaining a Keycloak instance (JVM-based, resource-heavy).
    *   **Complexity:** Keycloak has a steep learning curve and complex configuration.
