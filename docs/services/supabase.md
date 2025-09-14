# Supabase Ecosystem

Supabase provides the core database infrastructure for the GenAI Vanilla Stack, including PostgreSQL database, authentication, storage, realtime subscriptions, and a management dashboard.

## Overview

The Supabase ecosystem consists of multiple integrated services:

- **PostgreSQL Database** - Primary database with pgvector and PostGIS extensions
- **Auth Service (GoTrue)** - User authentication and JWT management  
- **Storage Service** - File storage and management
- **API Service (PostgREST)** - Auto-generated REST API
- **Realtime Service** - WebSocket connections for live updates
- **Studio Dashboard** - Web-based database management interface

## Database Setup Process

The database initialization follows a two-stage process managed by Docker Compose dependencies:

### 1. Base Database Initialization (`supabase-db` service)

- Uses the standard `supabase/postgres` image
- On first start with an empty data volume, runs internal initialization scripts from `/docker-entrypoint-initdb.d/`
- Base scripts handle:
  - Setting up PostgreSQL
  - Creating the database specified by `POSTGRES_DB`
  - Creating standard Supabase roles (`anon`, `authenticated`, `service_role`)
  - Enabling necessary extensions (`pgcrypto`, `uuid-ossp`)
  - Setting up basic `auth` and `storage` schemas

**IMPORTANT**: The `SUPABASE_DB_USER` in your `.env` file must be set to `supabase_admin`. This is required by the base image's internal scripts.

### 2. Custom Post-Initialization (`supabase-db-init` service)

- A dedicated, short-lived service using `postgres:alpine` image
- Depends on `supabase-db` and waits until it's ready using `pg_isready`
- Executes all `.sql` files from `./supabase/db/scripts/` directory in alphabetical order
- Custom scripts handle project-specific setup:
  - Ensuring extensions like `vector` and `postgis` are enabled (`01-extensions.sql`)
  - Ensuring schemas like `auth` and `storage` exist (`02-schemas.sql`)
  - Creating necessary custom types for Supabase Auth (`03-auth-types.sql`)
  - Creating custom public tables like `users` and `llms` (`04-public-tables.sql`)
  - Granting appropriate permissions to standard roles (`05-permissions.sql`)
  - Creating custom functions like `public.health` (`06-functions.sql`)
  - Inserting seed data like default LLMs (`07-seed-data.sql`)

All custom SQL scripts use `IF NOT EXISTS` logic to allow safe re-runs.

### 3. Service Dependencies

Most other services have `depends_on: { supabase-db-init: { condition: service_completed_successfully } }` to ensure they only start after both base and custom initialization are complete.

## Authentication System

The stack uses Supabase Auth (GoTrue) for user authentication and management with JWT tokens.

### Key Components

**supabase-auth (GoTrue)**:
- Issues JWTs upon successful login/sign-up
- Validates JWTs presented to its endpoints  
- Configured via `GOTRUE_*` environment variables
- Sign-ups enabled by default (`GOTRUE_DISABLE_SIGNUP="false"`)
- Emails auto-confirmed for local development (`GOTRUE_MAILER_AUTOCONFIRM="true"`)

**supabase-api (PostgREST)**:
- Expects valid JWT in `Authorization: Bearer <token>` header
- Validates JWT signature using `PGRST_JWT_SECRET` (shared with auth)
- Enforces database permissions based on JWT role claim via PostgreSQL RLS

**supabase-storage**:
- Uses JWTs passed via Kong to enforce storage access policies

**kong-api-gateway**:
- Routes authenticated requests to backend services
- Relies on upstream services for JWT validation

### JWT Keys (.env file)

- `SUPABASE_JWT_SECRET`: Secret key for signing/verifying JWTs (consistent across all services)
- `SUPABASE_ANON_KEY`: Pre-generated JWT for `anon` role (public access)
- `SUPABASE_SERVICE_KEY`: Pre-generated JWT for `service_role` (admin privileges)

### Setup and Usage

1. **Generate Keys**: start.py automatically generates secure JWT keys during first run or cold start
2. **Client Authentication**: Implement login flow using `/auth/v1/token?grant_type=password`
3. **Anonymous Access**: Use `SUPABASE_ANON_KEY` for public requests
4. **Service Role Access**: Use `SUPABASE_SERVICE_KEY` for admin operations (handle securely)
5. **User Management**: Use Supabase Studio interface at `http://localhost:${SUPABASE_STUDIO_PORT}`

## Individual Services

### PostgreSQL Database

**Access**: Direct connection via standard PostgreSQL client
**Port**: `${SUPABASE_DB_PORT}` (default: 63005)
**Extensions**: pgvector, PostGIS, uuid-ossp, pgcrypto

### Auth Service (GoTrue)

**Access**: `http://localhost:${SUPABASE_AUTH_PORT}` (default: 63006)
**Purpose**: User registration, login, password recovery, email confirmation
**Features**: JWT authentication, user management, password policies

### Storage Service

**Access**: `http://localhost:${SUPABASE_STORAGE_PORT}` (default: 63008)
**Features**:
- Secure file storage and management
- Access control via database policies
- Integration with authentication system
- Support for various file types

### API Service (PostgREST)

**Access**: `http://localhost:${SUPABASE_API_PORT}` (default: 63007)
**Purpose**: Auto-generated REST API for database operations
**Features**:
- Automatic API generation from database schema
- Row Level Security (RLS) enforcement
- Real-time subscriptions support
- GraphQL endpoint available

### Realtime Service

**Access**: WebSocket at `http://localhost:${SUPABASE_REALTIME_PORT}` (default: 63010)
**Purpose**: Live database change notifications
**Features**:
- Real-time database change notifications
- WebSocket-based connections
- Subscription management
- Integration with frontend applications

### Studio Dashboard

**Access**: `http://localhost:${SUPABASE_STUDIO_PORT}` (default: 63009)
**Purpose**: Web-based database management interface
**Credentials**: admin@example.com / changeme123 (configurable)
**Features**:
- Database schema visualization
- Query editor and runner
- User management interface
- Storage file browser
- Real-time monitoring

## Environment Variables

Key environment variables for Supabase configuration:

```bash
# Database
POSTGRES_DB=postgres
SUPABASE_DB_USER=supabase_admin
SUPABASE_DB_PASSWORD=your_password
SUPABASE_DB_PORT=63005

# Authentication
SUPABASE_JWT_SECRET=your_jwt_secret
SUPABASE_ANON_KEY=generated_anon_key
SUPABASE_SERVICE_KEY=generated_service_key

# Service Ports
SUPABASE_AUTH_PORT=63006
SUPABASE_API_PORT=63007
SUPABASE_STORAGE_PORT=63008
SUPABASE_STUDIO_PORT=63009
SUPABASE_REALTIME_PORT=63010

# Dashboard Credentials
DASHBOARD_USERNAME=admin@example.com
DASHBOARD_PASSWORD=changeme123
```

## Integration Points

**Backend API**: Uses Supabase for data persistence and user management
**Open WebUI**: Integrates with authentication for user sessions
**n8n**: Uses PostgreSQL for workflow storage and execution history
**Kong Gateway**: Routes requests to appropriate Supabase services with authentication

## Common Operations

### Connect to Database
```bash
# Using psql
psql -h localhost -p ${SUPABASE_DB_PORT} -U supabase_admin -d postgres

# Using Docker
docker exec -it genai-supabase-db psql -U supabase_admin -d postgres
```

### Check Service Health
```bash
# Database
docker exec genai-supabase-db pg_isready

# Services
curl http://localhost:${SUPABASE_API_PORT}/health
curl http://localhost:${SUPABASE_AUTH_PORT}/health
```

### View Logs
```bash
docker logs genai-supabase-db -f
docker logs genai-supabase-auth -f
docker logs genai-supabase-api -f
docker logs genai-supabase-studio -f
```

## Troubleshooting

**Database connection issues**: Verify SUPABASE_DB_USER is set to `supabase_admin`
**Auth service errors**: Check JWT secret consistency across services
**Studio access issues**: Verify dashboard credentials in .env file
**Initialization failures**: Check supabase-db-init logs for SQL script errors

For more troubleshooting help, see [../quick-start/troubleshooting.md](../quick-start/troubleshooting.md).