import os
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file in the root directory
load_dotenv()

def get_db_config(prefix):
    """Fetches database configuration from environment variables."""
    config = {
        'host': os.getenv(f'{prefix}_DB_HOST'),
        'user': os.getenv(f'{prefix}_DB_USER'),
        'password': os.getenv(f'{prefix}_DB_PASSWORD'),
        'dbname': os.getenv(f'{prefix}_DB_NAME'),
        'port': os.getenv(f'{prefix}_DB_PORT', '5432'),
    }
    # Check if all required environment variables are set
    required_vars = ['host', 'user', 'password', 'dbname']
    missing_vars = [key for key in required_vars if not config[key]]
    if missing_vars:
        print(f"Error: Missing database configuration for {prefix}. Please check your .env file for {', '.join(f'{prefix}_DB_{v.upper()}' for v in missing_vars)}.")
        sys.exit(1)
    return config

PROD_DB = get_db_config('PROD')
LOCAL_DB = get_db_config('LOCAL')

def create_backup():
    """Dumps the production database to a .sql file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dump_file = f'db_dump_prod_{timestamp}.sql'
    
    # Create pg_dump command, using the password from the environment
    dump_cmd = (
        f"PGPASSWORD='{PROD_DB['password']}' pg_dump "
        f"-h {PROD_DB['host']} -U {PROD_DB['user']} -d {PROD_DB['dbname']} "
        f"-p {PROD_DB['port']} -f {dump_file} --clean --no-owner --no-acl"
    )
    
    print("Creating backup from production database...")
    try:
        process = subprocess.run(dump_cmd, shell=True, check=True, capture_output=True, text=True)
        print("Backup created successfully.")
        return dump_file
    except subprocess.CalledProcessError as e:
        print("Error creating backup:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        raise

def restore_local_db(dump_file):
    """Restores the dump file to the local database."""
    env = os.environ.copy()
    env['PGPASSWORD'] = LOCAL_DB['password']

    common_args = [
        '-h', LOCAL_DB['host'],
        '-U', LOCAL_DB['user'],
        '-p', LOCAL_DB['port']
    ]
    
    # Terminate existing connections
    print("Terminating existing connections to local database...")
    try:
        subprocess.run(
            ['psql', *common_args, '-d', 'postgres', '-c', 
             f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{LOCAL_DB['dbname']}' AND pid <> pg_backend_pid();"],
            env=env, check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Could not terminate connections (this might be okay): {e.stderr}")

    # Drop the existing database
    print("Dropping local database...")
    try:
        subprocess.run(['dropdb', *common_args, LOCAL_DB['dbname']], env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Could not drop database (this might be okay): {e.stderr}")

    # Create a fresh database
    print("Creating fresh local database...")
    try:
        subprocess.run(['createdb', *common_args, LOCAL_DB['dbname']], env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error creating database:")
        print(f"STDERR: {e.stderr}")
        raise

    # Restore the backup
    print(f"Restoring backup to '{LOCAL_DB['dbname']}'...")
    try:
        subprocess.run(
            ['psql', *common_args, '-d', LOCAL_DB['dbname'], '-f', dump_file],
            env=env, check=True, capture_output=True, text=True
        )
        print("Restore completed successfully.")
    except subprocess.CalledProcessError as e:
        print("Error restoring database:")
        print(f"STDERR: {e.stderr}")
        raise

def cleanup(dump_file):
    """Removes the temporary dump file."""
    if os.path.exists(dump_file):
        os.remove(dump_file)
        print(f"Cleaned up temporary dump file: {dump_file}")

def main():
    dump_file = None
    try:
        dump_file = create_backup()
        restore_local_db(dump_file)
        print("\nDatabase sync from production to local completed successfully!")
    except Exception as e:
        print(f"\nAn error occurred during DB sync: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        if dump_file:
            cleanup(dump_file)

if __name__ == "__main__":
    main() 