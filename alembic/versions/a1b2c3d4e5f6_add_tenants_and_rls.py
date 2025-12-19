"""Add tenants table and RLS policies

Revision ID: a1b2c3d4e5f6
Revises: 76b493660380
Create Date: 2025-12-19 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '76b493660380'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Enable RLS on events and event_entities
    # We must ensure the tables exist first. In previous migrations they should have been created.
    # The error 'relation "events" does not exist' suggests that maybe 76b493660380 didn't run correctly or 
    # the 16ac566932d6_initial_migration.py created them but they were lost or schema mismatch.
    # However, since we are in async mode, sometimes 'execute' needs to be careful.
    
    # Check if tables exist before applying RLS? No, Alembic assumes we follow the chain.
    # The issue might be that 76b493660380 uses 'op.execute("TRUNCATE ...")' which might have failed silently 
    # or the table creation in 16ac566932d6 was rolled back?
    
    # Re-verify the table creation. 
    # If the user started fresh, the DB might be empty.
    # 16ac566932d6 creates the tables.
    
    op.execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE event_entities ENABLE ROW LEVEL SECURITY")

    # 3. Create RLS Policies
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON events
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
    """)
    
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON event_entities
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
    """)

    # 4. Set default value for tenant_id to use the session variable
    # We use 'current_setting(..., true)' to avoid errors if variable is not set (returns null), 
    # but the column is nullable=False, so insert will fail if not set, which is desired.
    op.alter_column('events', 'tenant_id', server_default=sa.text("current_setting('app.tenant_id', true)"))
    op.alter_column('event_entities', 'tenant_id', server_default=sa.text("current_setting('app.tenant_id', true)"))
    
    op.execute("ALTER TABLE events FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE event_entities FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE event_entities NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE events NO FORCE ROW LEVEL SECURITY")
    
    op.alter_column('event_entities', 'tenant_id', server_default=None)
    op.alter_column('events', 'tenant_id', server_default=None)

    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON event_entities")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON events")
    
    op.execute("ALTER TABLE event_entities DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE events DISABLE ROW LEVEL SECURITY")

    op.drop_table('tenants')
