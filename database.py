import psycopg2
from contextlib import contextmanager
from config import Settings

settings = Settings()

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(settings.DB_CONNECTION)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Step 1: Drop and recreate enums
            for enum_name, values in [
                ('priority_enum', ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
                ('status_enum', ['ACTIVE', 'INACTIVE', 'RESOLVED', 'ACKNOWLEDGED']),
                ('notification_status_enum', ['SUCCESS', 'FAILED', 'RETRY', 'PENDING'])
            ]:
                # Drop the enum if it exists
                cur.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE;")
                # Create the enum
                cur.execute(f"""
                    CREATE TYPE {enum_name} AS ENUM ({', '.join(f"'{v}'" for v in values)});
                """)
                conn.commit()
            # Step 1: Create enums explicitly, rolling back if they already exist
            for enum_name, values in [
                ('priority_enum', ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
                ('status_enum', ['ACTIVE', 'INACTIVE', 'RESOLVED', 'ACKNOWLEDGED']),
                ('notification_status_enum', ['SUCCESS', 'FAILED', 'RETRY', 'PENDING'])
            ]:
                try:
                    cur.execute(f"""
                        CREATE TYPE {enum_name} AS ENUM ({', '.join(f"'{v}'" for v in values)});
                    """)
                except psycopg2.errors.DuplicateObject:
                    conn.rollback()  # Roll back if enum already exists
                else:
                    conn.commit()  # Commit if enum was created

            # Step 2: Create tables (order matters due to foreign key dependencies)
            # data_source table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_source (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    connection_details JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # team table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS team (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT
                );
            """)

            # users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    team_id UUID REFERENCES team(id),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # alert_config table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alert_config (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    query TEXT NOT NULL,
                    data_source_id UUID REFERENCES data_source(id),
                    trigger_condition TEXT,
                    schedule VARCHAR(50) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    created_by UUID REFERENCES users(id),
                    status status_enum DEFAULT 'ACTIVE',
                    notification_channels JSONB NOT NULL,
                    priority priority_enum DEFAULT 'MEDIUM'
                );
            """)
            # Create tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alert_config (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    query TEXT NOT NULL,
                    data_source_id UUID REFERENCES data_source(id),
                    trigger_condition TEXT,
                    schedule VARCHAR(50) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    created_by UUID REFERENCES users(id),
                    status status_enum DEFAULT 'ACTIVE',
                    notification_channels JSONB NOT NULL,
                    priority priority_enum DEFAULT 'MEDIUM'
                );
            """)

            # Migration: Add priority column if missing
            cur.execute("""
                ALTER TABLE alert_config
                ADD COLUMN IF NOT EXISTS priority priority_enum DEFAULT 'MEDIUM';
            """)
            cur.execute("""
            ALTER TABLE alert_config
            ADD COLUMN IF NOT EXISTS status status_enum DEFAULT 'ACTIVE';
                """)
            # incident table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS incident (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    alert_config_id UUID REFERENCES alert_config(id),
                    status status_enum DEFAULT 'ACTIVE',
                    priority priority_enum,
                    assigned_team UUID REFERENCES team(id),
                    assigned_user UUID REFERENCES users(id),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMPTZ,
                    incident_data JSONB
                );
            """)
            
            # Migration: Add priority column if missing
            cur.execute("""
                ALTER TABLE incident
                ADD COLUMN IF NOT EXISTS priority priority_enum DEFAULT 'MEDIUM';
            """)
            cur.execute("""
            ALTER TABLE incident
            ADD COLUMN IF NOT EXISTS status status_enum DEFAULT 'ACTIVE';
                """)
            # notification table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notification (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    incident_id UUID REFERENCES incident(id),
                    channel VARCHAR(50) NOT NULL,
                    status notification_status_enum DEFAULT 'PENDING',
                    sent_at TIMESTAMPTZ,
                    recipient VARCHAR(255) NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at TIMESTAMPTZ
                );
            """)
            cur.execute("""
                ALTER TABLE notification
                ADD COLUMN IF NOT EXISTS priority priority_enum DEFAULT 'MEDIUM';
            """)
            cur.execute("""
                            ALTER TABLE notification
                            ADD COLUMN status notification_status_enum DEFAULT 'PENDING';
                        """)
            # activity table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activity (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    incident_id UUID REFERENCES incident(id),
                    user_id UUID REFERENCES users(id),
                    action VARCHAR(50) NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # ai_analysis table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    incident_id UUID REFERENCES incident(id),
                    agent_name VARCHAR(100) NOT NULL,
                    analysis_result JSONB NOT NULL,
                    confidence FLOAT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()

# Test it
if __name__ == "__main__":
    init_db()
    print("Database initialization completed successfully.")