import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.api.deps import get_idp_provider
from sqlalchemy.pool import NullPool
from alembic.config import Config
from alembic import command
import os
from sqlalchemy import text
from tests.mocks import MockIdPProvider

# Use a separate database for testing or the same one (be careful!)
TEST_DATABASE_URL = settings.DATABASE_URL 

engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    """
    Apply Alembic migrations to the test database.
    """
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield
    # Cleanup if needed

@pytest.fixture(scope="function", autouse=True)
async def cleanup_data():
    """
    Truncate tables after each test to ensure clean state while keeping schema/policies.
    """
    async with engine.begin() as conn:
        try:
            await conn.execute(text("TRUNCATE TABLE event_entities, events, tenants CASCADE"))
        except Exception as e:
            print(f"Cleanup failed (tables might not exist): {e}")
            pass
    yield

@pytest.fixture
async def db_session():
    """
    Standalone session for test assertions/setup.
    """
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def mock_idp():
    """
    Provides a mock IdP that bypasses real Keycloak.
    """
    provider = MockIdPProvider()
    app.dependency_overrides[get_idp_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_idp_provider, None)

@pytest.fixture
def auth_headers(mock_idp):
    """
    Returns a helper function to generate auth headers for a given tenant.
    """
    def _headers(tenant_id="default-tenant"):
        token = mock_idp.mint_token(tenant_id)
        return {"Authorization": f"Bearer {token}"}
    return _headers

@pytest.fixture
async def client(mock_idp):
    """
    Client that spawns a new DB session for each request (mimics production).
    Automatically mocks IdP.
    """
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
