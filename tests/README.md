# E2E Testing for Curiosity Coach

This directory contains the end-to-end testing setup for the Curiosity Coach application. The tests are designed to run against locally-hosted `Backend` and `Brain` services and a local PostgreSQL database.

## 1. Setup

### a. Create and Activate Virtual Environment
It is crucial to run the tests in a dedicated virtual environment to manage dependencies.

```bash
# From the root of the project, navigate into the tests directory
cd tests

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### b. Install Dependencies
Install all the required Python packages for testing.

```bash
# Make sure your venv is activated
pip install -r requirements.txt
```

### c. Configure Environment Variables
The tests and supporting scripts require credentials and configuration details, which should be stored in a `.env` file.

1.  Create a `.env` file in this `tests` directory by copying the example file:
    ```bash
    cp .env.example .env
    ```
2.  Open the `.env` file and fill in the values for your production and local databases, as well as the test user's phone number.

### d. Run Local Services
Before running the tests, you must have the `Backend` and `Brain` services running locally.

-   **Backend Service:** Navigate to the `backend` directory and run `./run.sh`.
-   **Brain Service:** Navigate to the `Brain` directory and run `./run.sh`.

The test suite expects the backend to be on `http://127.0.0.1:5000` by default and the brain to be on `http://127.0.0.1:5001`, but you can configure this in your `.env` file.

## 2. Running Tests

### a. Database Synchronization
The test suite automatically syncs your local database with production data before running. The first time you run the tests, it will find all conversations that need a "memory" and process them.

The setup is handled automatically by the `pytest` fixture in `conftest.py`, which executes the `scripts/sync_db.py` script.

### b. Executing Tests
With your virtual environment activated and services running, you can run the test suite using `pytest`.

```bash
# From the tests directory
pytest -v
``` 