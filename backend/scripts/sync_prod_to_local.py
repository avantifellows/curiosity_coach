#!/usr/bin/env python3
"""
Script to sync production database to local database.

This script will:
1. Read database credentials from .env.local and .env.prod files
2. Completely clean up the local PostgreSQL database (drop and recreate)
3. Download a complete dump (schema + data) from the production database
4. Load the production dump onto the local database (includes all tables, data, sequences, constraints)
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def load_env_file(env_file_path):
    """Load environment variables from a file."""
    if not os.path.exists(env_file_path):
        print(f"ERROR: Environment file {env_file_path} not found!")
        sys.exit(1)
    
    # Create a temporary environment to load variables
    env_vars = {}
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
    
    return env_vars


def get_db_config(env_vars, env_name):
    """Extract database configuration from environment variables."""
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    
    config = {}
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            print(f"ERROR: {var} not found or empty in {env_name} environment file!")
            sys.exit(1)
        config[var.lower()] = env_vars[var]
    
    return config


def run_command(command, description, cwd=None):
    """Run a shell command and handle errors."""
    print(f"Running: {description}")
    print(f"Command: {' '.join(command) if isinstance(command, list) else command}")
    
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            shell=isinstance(command, str)
        )
        if result.stdout:
            print(f"Output: {result.stdout}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed!")
        print(f"Error code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        if e.stdout:
            print(f"Standard output: {e.stdout}")
        sys.exit(1)


def drop_all_connections(db_config):
    """Drop all connections to the database."""
    print("Dropping all connections to the local database...")
    
    # Connect to postgres database to drop connections to target database
    postgres_config = db_config.copy()
    postgres_config['db_name'] = 'postgres'
    
    try:
        conn = psycopg2.connect(
            host=postgres_config['db_host'],
            port=postgres_config['db_port'],
            database=postgres_config['db_name'],
            user=postgres_config['db_user'],
            password=postgres_config['db_password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Terminate all connections to the target database
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_config['db_name']}'
            AND pid <> pg_backend_pid()
        """)
        
        cur.close()
        conn.close()
        print("Successfully dropped all connections to the database.")
        
    except Exception as e:
        print(f"Warning: Could not drop connections: {e}")
        print("Continuing anyway...")


def clean_local_database(db_config):
    """Completely clean the local database."""
    print("Cleaning local database...")
    
    # First, drop all connections
    drop_all_connections(db_config)
    
    try:
        # Connect to postgres database to drop and recreate target database
        postgres_config = db_config.copy()
        postgres_config['db_name'] = 'postgres'
        
        conn = psycopg2.connect(
            host=postgres_config['db_host'],
            port=postgres_config['db_port'],
            database=postgres_config['db_name'],
            user=postgres_config['db_user'],
            password=postgres_config['db_password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Drop the database if it exists
        print(f"Dropping database {db_config['db_name']}...")
        cur.execute(f"DROP DATABASE IF EXISTS {db_config['db_name']}")
        
        # Create the database
        print(f"Creating database {db_config['db_name']}...")
        cur.execute(f"CREATE DATABASE {db_config['db_name']}")
        
        cur.close()
        conn.close()
        print("Local database cleaned successfully.")
        
    except Exception as e:
        print(f"ERROR: Failed to clean local database: {e}")
        sys.exit(1)


def run_alembic_upgrade():
    """Run alembic upgrade head to apply migrations."""
    print("Running alembic upgrade head...")
    
    # Get the backend directory (parent of scripts)
    backend_dir = Path(__file__).parent.parent
    
    run_command(
        ["alembic", "upgrade", "head"],
        "Alembic upgrade head",
        cwd=backend_dir
    )
    print("Alembic upgrade completed successfully.")


def create_pg_dump(prod_config, dump_file):
    """Create a PostgreSQL dump from production database."""
    print("Creating dump from production database...")
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = prod_config['db_password']
    
    command = [
        "pg_dump",
        "-h", prod_config['db_host'],
        "-p", prod_config['db_port'],
        "-U", prod_config['db_user'],
        "-d", prod_config['db_name'],
        "--verbose",
        "--no-owner",
        "--no-privileges",
        "-f", dump_file
    ]
    
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        print("Production database dump created successfully.")
        if result.stderr:  # pg_dump writes progress to stderr
            print(f"Dump output: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create production database dump!")
        print(f"Error code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)


def restore_pg_dump(local_config, dump_file):
    """Restore PostgreSQL dump to local database."""
    print("Restoring dump to local database...")
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = local_config['db_password']
    
    command = [
        "psql",
        "-h", local_config['db_host'],
        "-p", local_config['db_port'],
        "-U", local_config['db_user'],
        "-d", local_config['db_name'],
        "-f", dump_file
    ]
    
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        print("Database dump restored successfully.")
        if result.stdout:
            print(f"Restore output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to restore database dump!")
        print(f"Error code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        if e.stdout:
            print(f"Standard output: {e.stdout}")
        sys.exit(1)


def main():
    """Main function to orchestrate the database sync."""
    print("=== Starting Production to Local Database Sync ===")
    
    # Get the backend directory (parent of scripts)
    backend_dir = Path(__file__).parent.parent
    
    # Load environment files
    local_env_file = backend_dir / ".env.local"
    prod_env_file = backend_dir / ".env.prod"
    
    print(f"Loading local environment from: {local_env_file}")
    local_env_vars = load_env_file(local_env_file)
    local_db_config = get_db_config(local_env_vars, "local")
    
    print(f"Loading production environment from: {prod_env_file}")
    prod_env_vars = load_env_file(prod_env_file)
    prod_db_config = get_db_config(prod_env_vars, "production")
    
    print("\nDatabase configurations loaded successfully:")
    print(f"Local DB: {local_db_config['db_user']}@{local_db_config['db_host']}:{local_db_config['db_port']}/{local_db_config['db_name']}")
    print(f"Production DB: {prod_db_config['db_user']}@{prod_db_config['db_host']}:{prod_db_config['db_port']}/{prod_db_config['db_name']}")
    
    # Confirm with user
    response = input("\nThis will COMPLETELY WIPE your local database. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        sys.exit(0)
    
    # Step 1: Clean local database (creates empty database)
    clean_local_database(local_db_config)
    
    # Step 2: Create temporary dump file and sync data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
        dump_file = temp_file.name
    
    try:
        # Step 3: Create dump from production (this will include schema + data)
        create_pg_dump(prod_db_config, dump_file)
        
        # Step 4: Restore dump to local
        restore_pg_dump(local_db_config, dump_file)
        
        print("\n=== Database sync completed successfully! ===")
        
    finally:
        # Clean up temporary dump file
        if os.path.exists(dump_file):
            os.unlink(dump_file)
            print(f"Cleaned up temporary dump file: {dump_file}")


if __name__ == "__main__":
    main()
