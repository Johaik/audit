import pytest
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.core.auth.keycloak import KeycloakProvider
from app.config import settings

# Generate a temporary RSA key pair for testing JWTs
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
public_key = private_key.public_key()

pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')


@pytest.fixture
def mock_keycloak_provider():
    with patch("app.core.auth.keycloak.KeycloakAdmin") as MockAdmin, \
         patch("app.core.auth.keycloak.KeycloakOpenID") as MockOpenID:

         # Mock the public key method to return the bare base64 part of the key
         # because KeycloakProvider wraps it in PEM headers
         # For simplicity, we can patch `get_public_key` directly to return our exact PEM

         provider = KeycloakProvider()
         provider.get_public_key = lambda: pem_public
         yield provider


def test_validate_token_success(mock_keycloak_provider):
    """
    Test that a valid token with the correct audience is accepted.
    """
    payload = {
        "sub": "user123",
        "aud": settings.KEYCLOAK_AUDIENCE,
        "iss": "test-issuer",
        "exp": 9999999999
    }

    token = jwt.encode(payload, pem_private, algorithm="RS256")

    decoded = mock_keycloak_provider.validate_token(token)
    assert decoded["sub"] == "user123"
    assert decoded["aud"] == settings.KEYCLOAK_AUDIENCE


def test_validate_token_missing_audience(mock_keycloak_provider):
    """
    Test that a token missing the audience claim is rejected when verify_aud=True
    """
    payload = {
        "sub": "user123",
        "iss": "test-issuer",
        "exp": 9999999999
    }

    token = jwt.encode(payload, pem_private, algorithm="RS256")

    with pytest.raises(jwt.exceptions.MissingRequiredClaimError) as exc_info:
        mock_keycloak_provider.validate_token(token)

    assert "aud" in str(exc_info.value)


def test_validate_token_invalid_audience(mock_keycloak_provider):
    """
    Test that a token with a wrong audience claim is rejected when verify_aud=True
    """
    payload = {
        "sub": "user123",
        "aud": "wrong-audience",
        "iss": "test-issuer",
        "exp": 9999999999
    }

    token = jwt.encode(payload, pem_private, algorithm="RS256")

    with pytest.raises(jwt.exceptions.InvalidAudienceError) as exc_info:
        mock_keycloak_provider.validate_token(token)

    assert "Audience doesn't match" in str(exc_info.value)
