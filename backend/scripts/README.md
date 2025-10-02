# Backend Scripts

## sync_prod_to_local.py

This script synchronizes the production database to your local development database.

### Prerequisites

1. Ensure you have the following environment files in the backend directory:
   - `.env.local` - Contains local database credentials
   - `.env.prod` - Contains production database credentials

2. Both files should contain these variables:
   ```
   DB_HOST=
   DB_PORT=
   DB_NAME=
   DB_USER=
   DB_PASSWORD=
   ```

3. Required system dependencies:
   - PostgreSQL client tools (`pg_dump`, `psql`)
   - Python packages: `psycopg2-binary`, `python-dotenv` (already in requirements.txt)

### Usage

```bash
cd backend
python scripts/sync_prod_to_local.py
```

Or make it executable and run directly:
```bash
cd backend
./scripts/sync_prod_to_local.py
```

### What it does

1. **Validates environment files** - Checks that both `.env.local` and `.env.prod` exist and contain required database variables
2. **Completely cleans local database** - Drops and recreates the local database to ensure a clean state
3. **Runs migrations** - Executes `alembic upgrade head` to apply all database migrations
4. **Creates production dump** - Uses `pg_dump` to create a backup of the production database
5. **Restores to local** - Uses `psql` to restore the production data to the local database
6. **Cleans up** - Removes temporary dump files

### Safety Features

- **Confirmation prompt** - Asks for confirmation before wiping the local database
- **Error handling** - Exits immediately if any step fails
- **Environment validation** - Verifies all required environment variables are present
- **Connection dropping** - Safely terminates existing database connections before cleanup

### Important Notes

⚠️ **WARNING**: This script will completely wipe your local database. Make sure you have backups of any local data you want to keep.

The script assumes you have PostgreSQL client tools installed and accessible in your PATH.
