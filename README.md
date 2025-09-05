# Curiosity Coach

Curiosity Coach is a multi-component application designed to provide a coaching-like experience to users. It leverages Large Language Models (LLMs) to process user queries and formulate thoughtful responses, guiding users through various topics or problems.

## Architecture Overview

The application follows a microservices architecture, comprising three main services: Frontend, Backend, and Brain. These services are orchestrated and deployed on AWS, with infrastructure managed by Terraform.

-   **Frontend:** A web interface (likely React-based) allowing users to interact with the Curiosity Coach. Hosted on AWS S3.
-   **Backend:** A Python FastAPI application serving as the API layer. It handles business logic, user authentication (if applicable), data persistence with RDS PostgreSQL, and communication with the Brain service via SQS. Hosted on AWS Lambda with a Function URL.
-   **Brain:** A Python application (also deployable on AWS Lambda) responsible for the core intelligent processing. It consumes tasks from SQS, interacts with LLMs (e.g., OpenAI, Groq), uses a flow configuration from S3, and sends results back to the Backend.

## Services

Each service has its own detailed README file providing specific information about its functionality, setup, and local development.

-   ### [Frontend Service (`curiosity-coach-frontend/`)](curiosity-coach-frontend/README.md)
    The user-facing web application.
    *   **Location:** `curiosity-coach-frontend/README.md`

-   ### [Backend Service (`backend/`)](backend/README.md)
    Handles API requests, business logic, database interactions (PostgreSQL), and queuing tasks for the Brain.
    *   **Location:** `backend/README.md`

-   ### [Brain Service (`Brain/`)](Brain/README.md)
    The intelligent core that processes queries using LLMs and contextual data.
    *   **Location:** `Brain/README.md`

## Infrastructure as Code (IaC)

The entire cloud infrastructure for Curiosity Coach is defined and managed using Terraform. The configuration files are located in the `terraform/` directory at the root of the project.

-   `terraform/frontend.tf`: Defines resources for the frontend (S3 bucket for static website hosting).
-   `terraform/backend.tf`: Defines resources for the backend (Lambda, RDS, ECR, IAM roles, SQS queue access, VPC configurations).
-   `terraform/brain.tf`: Defines resources for the Brain service (Lambda, ECR, S3 for flow configuration, SQS queue and trigger, IAM roles).
-   `terraform/variables.tf`: Contains common variables used across the Terraform configurations.
-   `terraform/providers.tf` (if present, or part of main.tf): Configures AWS provider.
-   `terraform/outputs.tf` (if present): Defines outputs like service URLs.

For details on deploying and managing the infrastructure, refer to the README within the `terraform/` directory (you may need to create one if it doesn't exist) and the individual service READMEs for build/push instructions that might be prerequisites for Terraform deployment.

## User Flow and System Diagram

The following diagram illustrates the typical flow of a user query through the Curiosity Coach system:

```mermaid
graph TD
    User((User)) --> Frontend_S3{Frontend Application (S3)};
    Frontend_S3 -- API Call (HTTPS) --> Backend_Lambda[Backend Lambda (Function URL)];
    Backend_Lambda -- Read/Write --> RDS_DB[(RDS PostgreSQL)];
    Backend_Lambda -- Sends Task --> SQS_Queue[SQS Queue];
    SQS_Queue -- Triggers --> Brain_Lambda[Brain Lambda];
    Brain_Lambda -- Reads Config --> S3_FlowConfig[S3 (flow_config.json)];
    Brain_Lambda -- Interacts --> LLM_Services[LLM APIs (e.g., OpenAI, Groq)];
    Brain_Lambda -- Sends Result (HTTP Callback) --> Backend_Lambda;
    Backend_Lambda -- API Response (HTTPS) --> Frontend_S3;
    Frontend_S3 -- Displays to --> User;
```

**Flow Description:**

1.  **User Interaction:** The user interacts with the Frontend application hosted on S3.
2.  **API Request:** The Frontend sends an API request (e.g., a query) to the Backend Lambda via its Function URL.
3.  **Backend Processing (Initial):**
    *   The Backend Lambda processes the request.
    *   It may read from or write to the RDS PostgreSQL database (e.g., save conversation history, user data).
    *   It then sends a message/task to an SQS queue for the Brain service to handle the computationally intensive or LLM-dependent part.
4.  **SQS to Brain:** The SQS queue triggers the Brain Lambda function.
5.  **Brain Processing:**
    *   The Brain Lambda consumes the message from SQS.
    *   It reads a `flow_config.json` from an S3 bucket to guide its processing logic.
    *   It interacts with external LLM services (like OpenAI or Groq) to generate a response or analysis.
    *   Once processing is complete, the Brain Lambda sends the result back to the Backend Lambda via an HTTP callback to a specific endpoint on the Backend.
6.  **Backend Processing (Final):**
    *   The Backend Lambda receives the callback from the Brain.
    *   It processes this result, potentially updating the RDS database.
    *   It formulates the final API response.
7.  **API Response:** The Backend Lambda sends the API response back to the Frontend.
8.  **Display to User:** The Frontend displays the information/response to the user.

## Getting Started

### Local Development

To run the application locally for development:

#### Prerequisites
*   Node.js and npm (for the frontend)
*   Python (for backend and brain services)
*   PostgreSQL (for local database)
*   `uv` (for backend Python environment)

#### Environment Files Setup
Before running the services, you'll need to obtain the environment files from another developer and place them in the following locations:

```
backend/.env.local
backend/.env.prod
backend/.env.staging
Brain/src/.env
Brain/src/.env.prod
curiosity-coach-frontend/.env.local
curiosity-coach-frontend/.env.prod
```

#### Running the Services

1.  **Clone the Repository:**
    ```bash
    # git clone <repository-url>
    cd curiosity-coach
    ```

2.  **Backend Service:**
    ```bash
    cd backend
    ./run.sh
    ```

3.  **Brain Service:**
    ```bash
    cd Brain
    ./run.sh
    ```

4.  **Frontend Service:**
    ```bash
    cd curiosity-coach-frontend
    npm install
    npm run start
    ```

#### Database Setup

To sync the production database to your local environment:

```bash
cd backend
python scripts/sync_prod_to_local.py
```

**Note:** This will completely wipe your local database and replace it with production data. Make sure you have the required environment files (`.env.local` and `.env.prod`) configured before running this script.

### Production Deployment

For production deployment:

1.  **Prerequisites:**
    *   AWS Account and configured AWS CLI.
    *   Terraform CLI.
    *   Docker.
2.  **Service-Specific Setup:** Follow the instructions in the `README.md` files located within each service directory (`curiosity-coach-frontend/`, `backend/`, `Brain/`) for detailed setup, environment configuration, and build instructions.
3.  **Infrastructure Deployment:** Use Terraform commands (`terraform init`, `terraform plan`, `terraform apply`) in the `terraform/` directory to deploy the AWS infrastructure. Ensure any prerequisite image pushes to ECR are done as per service READMEs if not fully automated by Terraform `null_resource` provisioners.

## Contributing

Please refer to contributing guidelines if available (e.g., `CONTRIBUTING.md`). (Currently, a placeholder).
-   Follow coding standards.
-   Write tests for new features.
-   Ensure documentation is updated. 

