# Project Overview (Both technical and non-technical)

This document provides a technical overview of the Curiosity Coach project.

## Project Overview (Both technical and non-technical)

The Curiosity Coach project is a conversational AI application designed to help students learn by fostering curiosity. It consists of a frontend, a backend, and a "Brain" service.

## Architecture

The project follows a microservices architecture, with three main components:

1.  **Frontend:** A React application that provides the user interface for the chat.
2.  **Backend:** A FastAPI application that handles user authentication, conversation management, and acts as a gateway to the Brain service.
3.  **Brain:** A Python service that is responsible for processing user messages and generating responses.

The services are deployed on AWS using Terraform.

### High-Level System Diagram

```mermaid
graph TD
    User((User)) --> Frontend_S3{"Frontend (S3) via CloudFront"}
    Frontend_S3 -- "API Call (HTTPS)" --> APIGW_Backend["API Gateway (Backend HTTP API)"]
    APIGW_Backend --> Backend_Lambda["Backend Lambda (FastAPI + Mangum)"]
    Backend_Lambda -- "Read/Write" --> RDS_DB[("RDS PostgreSQL")]
    Backend_Lambda -- "Enqueue" --> SQS_Queue["SQS Queue"]
    SQS_Queue -- "Triggers" --> Brain_Lambda["Brain Lambda (FastAPI + Mangum)"]
    Brain_Lambda -- "Reads Config" --> S3_FlowConfig["S3 (flow_config.json)"]
    Brain_Lambda -- "Interacts" --> LLM_Services["LLM APIs (OpenAI, Groq)"]
    Brain_Lambda -- "HTTP Callback" --> Backend_Lambda
    APIGW_Backend -- "HTTPS" --> Frontend_S3
    Frontend_S3 -- "Displays to" --> User
```

## Services

### 1. Frontend (`curiosity-coach-frontend/`)

*   **Technology:** React, TypeScript, Tailwind CSS, Material UI.
*   **Functionality:**
    *   User login (identifier-based: phone number or name).
    *   Real-time chat interface for conversations with the AI.
    *   Message history persistence.
    *   Interface for testing different prompts.
    *   Interface for viewing different versions of prompts.
    *   A modal for users to provide feedback (thumbs up/down and optional text).
*   **Infrastructure:**
    *   Hosted on an S3 bucket.
    *   Served by a CloudFront distribution.
    *   DNS managed by Cloudflare.

### 2. Backend (`backend/`)

*   **Technology:** Python 3.9+, FastAPI, SQLAlchemy, Alembic, PostgreSQL. Deployed on AWS Lambda using Mangum behind API Gateway (HTTP API).
*   **Key Libraries:** `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `alembic`, `pydantic`, `boto3`, `mangum`, `python-dotenv`, `passlib`, `python-jose`.
*   **Functionality:**
    *   User authentication (phone number based).
    *   CRUD operations for users, conversations, messages, prompts, prompt versions, memories, and user personas.
    *   An endpoint (`/api/feedback/`) to receive and store user feedback.
    *   An endpoint (`/api/tasks/trigger-memory-generation`) to initiate memory generation for recently ended conversations.
    *   An endpoint (`/api/tasks/trigger-user-persona-generation`) to initiate persona generation for users.
    *   Forwards user messages to the Brain service via an SQS queue and enqueues batch tasks for memory and persona generation.
    *   Receives responses from the Brain service via an HTTP callback.
    *   Internal read for a conversation's memory at `/api/internal/conversations/{conversation_id}/memory` (used by Brain).
    *   Internal read for a user's persona at `/api/internal/users/{user_id}/persona` (used by Brain).
    *   Locally, the backend can talk directly to the Brain service, bypassing SQS.
*   **Infrastructure:**
    *   Runs as a Dockerized FastAPI app on AWS Lambda (Mangum).
    *   Exposed via API Gateway (HTTP API).
    *   Uses an RDS for PostgreSQL database.
    *   Uses an SQS queue to communicate with the Brain service.

### 3. Brain (`Brain/`)

*   **Technology:** Python 3.11, FastAPI (local), Mangum on AWS Lambda (HTTP API via API Gateway).
*   **Key Libraries:** `fastapi`, `uvicorn`, `jinja2`, `requests`, `httpx`, `python-dotenv`, `groq`, `openai`, `mangum`, `boto3`, `pydantic`.
*   **Functionality:**
    *   Processes user messages and returns structured pipeline data. Supports simplified single-step mode by default.
    *   Handles SQS-driven batch tasks: conversation memory generation and user persona generation.
    *   Loads prompts from files; initializes prompts/versions in the backend on startup when missing.
    *   Configurable pipeline (FlowConfig) stored in S3 with `/get-config` and `/set-config` endpoints.
    *   Interacts with the backend via internal endpoints for history/persona/memory; sends HTTP callbacks to persist AI responses and pipeline data.
    *   Supports prompt-time injection of conversation memory via placeholders `{{CONVERSATION_MEMORY}}` and `{{CONVERSATION_MEMORY__key1__key2}}` (keys derived from `ConversationMemoryData`).
    *   Supports prompt-time injection of user persona via placeholders `{{USER_PERSONA}}` and `{{USER_PERSONA__key1__key2}}` (keys derived from `UserPersonaData`; currently only `persona`).
*   **Infrastructure:**
    *   Dockerized FastAPI app on AWS Lambda (Mangum) behind API Gateway.
    *   Triggered by messages from the SQS queue from the backend; also exposes HTTP endpoints.
    *   Stores its `flow_config.json` in an S3 bucket.

## Database Schema

The backend uses a PostgreSQL database with the following tables:

*   `users`: Stores user information (either `phone_number` or `name`).
*   `conversations`: Stores conversation metadata (user, title, etc.).
*   `conversation_memories`: Stores structured summaries of conversations, generated by the Brain.
*   `user_personas`: Stores a structured JSON persona per user (1:1), generated by the Brain from conversation memories.
*   `messages`: Stores the messages in each conversation.
*   `user_feedback`: Stores user-submitted feedback JSON under `feedback_data`.
*   `message_pipeline_data`: Stores additional data about the message processing pipeline from the Brain service.
*   `prompts`: Stores different types of prompts used by the Brain service.
*   `prompt_versions`: Stores different versions of each prompt.

### Database Schema Diagram
```mermaid
erDiagram
    users {
        int id
        string phone_number "unique, nullable"
        string name "unique, nullable"
        datetime created_at
    }

    user_feedback {
        int id
        int user_id
        json feedback_data
        datetime created_at
    }

    user_personas {
        int id
        int user_id "unique"
        json persona_data
        datetime created_at
        datetime updated_at
    }

    conversations {
        int id
        int user_id
        string title
        int prompt_version_id "nullable"
        datetime created_at
        datetime updated_at
    }

    conversation_memories {
        int id
        int conversation_id "unique"
        json memory_data
        datetime created_at
        datetime updated_at
    }

    messages {
        int id
        int conversation_id
        text content
        bool is_user
        datetime timestamp
        int responds_to_message_id "nullable"
    }

    message_pipeline_data {
        int id
        int message_id "unique"
        json pipeline_data
        datetime created_at
    }

    prompts {
        int id
        string name "unique"
        text description "nullable"
        datetime created_at
        datetime updated_at
    }

    prompt_versions {
        int id
        int prompt_id
        int user_id "nullable"
        int version_number
        text prompt_text
        bool is_active
        bool is_production
        datetime created_at
    }

    users ||--o{ conversations : "has"
    users ||--|{ user_personas : "has one"
    users ||--o{ prompt_versions : "authors"
    users ||--o{ user_feedback : "provides"
    conversations ||--o{ messages : "contains"
    conversations }o--|| prompt_versions : "uses"
    conversations |o--|| conversation_memories : "has one"
    messages ||--|{ message_pipeline_data : "has"
    messages }o--o| messages : "responds to"
    prompts ||--o{ prompt_versions : "has versions"
```

---

# Developer Guide

This section contains information for developers to set up, run, test, and deploy the project.

## Local Development Setup

Each service (`frontend`, `backend`, `Brain`) contains a `run.sh` script to automate the setup and execution for local development.

### 1. Backend (`backend/`)
-   **Setup:**
    -   Navigate to the `backend/` directory.
    -   Create a `.env.local` file from the example. This file holds database credentials and other environment variables.
    -   Run `chmod +x run.sh`.
-   **Running:**
    -   Execute `./run.sh`.
    -   This script uses `uv` to create a virtual environment in `./venv`, installs dependencies from `requirements.lock`, and starts the FastAPI server on port 5000.

### 2. Brain (`Brain/`)
-   **Setup:**
    -   Navigate to the `Brain/` directory.
    -   Create a `src/.env` file. This file holds API keys for LLM services (OpenAI, Groq) and the backend callback URL.
    -   Run `chmod +x run.sh`.
-   **Running:**
    -   Execute `./run.sh`.
    -   This script uses `pip` to create a virtual environment in `./venv`, installs dependencies from `requirements.txt`, and starts the FastAPI server on port 8000.

### 3. Frontend (`curiosity-coach-frontend/`)
-   **Setup:**
    -   Navigate to the `curiosity-coach-frontend/` directory.
    -   Run `npm install` to install dependencies.
-   **Running:**
    -   Run `npm start` to start the React development server.

### Running All Services
You can start all services (Frontend, Backend, and Brain) concurrently using the "Start All Servers" task defined in `.vscode/tasks.json`, executable via the VS Code task runner.

## Database Migrations (Alembic)

The backend service uses Alembic to manage database schema changes.

1.  **Activate Environment:** `source backend/venv/bin/activate`
2.  **Apply Migrations:** To upgrade the database to the latest version, run `alembic upgrade head` from the `backend/` directory.
3.  **Create a New Migration:** After changing SQLAlchemy models in `src/models.py`, run `alembic revision -m "description" --autogenerate` to create a new migration script. Review the script before applying it.

## End-to-End Testing (`tests/`)

The project includes an E2E test suite that runs against the locally-hosted services.

1.  **Setup:**
    -   `cd tests`
    -   Create and activate a Python virtual environment: `python3 -m venv venv && source venv/bin/activate`.
    -   Install dependencies: `pip install -r requirements.txt`.
    -   Create a `.env` file from the example and fill in database credentials.
2.  **Running Tests:**
    -   Ensure the `Backend` and `Brain` services are running locally.
    -   Run `pytest -v` from the `tests/` directory.
    -   The test suite automatically handles database setup and synchronization.
    
### Example E2E flow tested

```100:131:/Users/deepanshmathur/Documents/AF/curiosity_coach/tests/test_e2e_messages.py
create_response = client.post(f"/api/conversations/{conversation_id}/messages", json=message_payload)
...
callback_response = client.post("/api/internal/brain_response", json=brain_payload)
```

## Infrastructure (Terraform)

The entire cloud infrastructure is managed using Terraform in the `terraform/` directory.

-   **Key Files:**
    -   `frontend.tf`: S3 + CloudFront for frontend, optional Cloudflare DNS.
    -   `backend.tf`: Backend ECR build/push, Lambda (container), API Gateway (HTTP API), RDS, SQS, VPC endpoints.
    -   `brain.tf`: Brain ECR build/push, Lambda (container), API Gateway (HTTP API), SQS (shared), S3 for FlowConfig, and event source mapping.
    -   `variables.tf`: Common variables.
-   **Deployment:**
    -   Navigate to the `terraform/` directory.
    -   Run `terraform init`, `terraform plan`, and `terraform apply`.
-   **Cloudflare for Custom Domain:**
    -   The `README-cloudflare.md` file provides instructions for setting up a custom domain for the CloudFront distribution using Cloudflare. This involves creating a `terraform.tfvars` file with your Cloudflare API key, email, and zone ID.

---

## Backend API Endpoints (summary)

- Authentication
  - POST `/api/auth/login` – identifier-based login (phone or name)
  - POST `/api/auth/login/phone` – legacy phone login
  - GET `/api/auth/me` – returns current user (Authorization: `Bearer <user_id>`)

- Conversations
  - GET `/api/conversations`
  - POST `/api/conversations` (optional body `{ title }`)
  - GET `/api/conversations/{id}`
  - DELETE `/api/conversations/{id}`
  - PUT `/api/conversations/{id}/title` (body `{ title }`)

- Messages
  - POST `/api/conversations/{conversation_id}/messages` (body `{ content, purpose? }`)
  - GET `/api/conversations/{conversation_id}/messages`
  - GET `/api/messages/{user_message_id}/response` (poll for AI reply)
  - GET `/api/messages/{ai_message_id}/pipeline_steps`

- Memories / Personas
  - POST `/api/memories` (upsert by `conversation_id`)
  - POST `/api/user-personas` (create/update by `user_id`)

- Prompts + Versions
  - GET `/api/prompts`, POST `/api/prompts`, GET `/api/prompts/{id_or_name}`, PUT/DELETE `/api/prompts/{id}`
  - POST `/api/prompts/{id_or_name}/versions?set_active=true`
  - GET `/api/prompts/{id_or_name}/versions`
  - POST `/api/prompts/{id_or_name}/versions/set-active`
  - GET `/api/prompts/{id_or_name}/versions/active`
  - GET `/api/prompts/{id_or_name}/versions/production`
  - POST `/api/prompts/{id_or_name}/versions/{version_number}/set-production`
  - DELETE `/api/prompts/{id_or_name}/versions/{version_number}/unset-production`
  - GET `/api/prompts/{id_or_name}/versions/earliest`

- Tasks
  - POST `/api/tasks/trigger-memory-generation`
  - POST `/api/tasks/trigger-memory-generation-sync`
  - POST `/api/tasks/trigger-user-persona-generation`
  - POST `/api/tasks/trigger-user-persona-generation-sync`
  - POST `/api/tasks/generate-memory-for-conversation/{conversation_id}` (query: `sync=true|false`)
  - POST `/api/tasks/generate-memories-for-user/{user_id}` (query: `only_needing`, `include_empty`, `clamp`, `sync`)
  - POST `/api/tasks/generate-persona-for-user/{user_id}` (query: `generate_conversation_memories_if_not_found`, `only_needing`, `include_empty`, `clamp`, `sync`)

- Feedback
  - POST `/api/feedback/` (body `{ feedback_data: {} }`)

- Health
  - GET `/api/health`, GET `/api/promptHealth`

- Internal (Brain only)
  - POST `/api/internal/brain_response` – save AI response and pipeline data
  - GET `/api/internal/conversations/{conversation_id}/messages_for_brain`
  - GET `/api/internal/users/{user_id}/memories`
  - GET `/api/internal/conversations/{conversation_id}/memory` – single conversation memory
  - GET `/api/internal/users/{user_id}/persona` – single user persona


## Brain HTTP/API contracts (summary)

- POST `/query` – processes chat/test-prompt payload
- POST `/tasks` – `GENERATE_MEMORY_BATCH` and `USER_PERSONA_GENERATION`
- GET `/get-config` – FlowConfig schema and current values (S3)
- POST `/set-config` – validate and save FlowConfig to S3

Brain sends HTTP callbacks to backend at `BACKEND_CALLBACK_BASE_URL + BACKEND_CALLBACK_ROUTE` (defaults to `/api/internal/brain_response`).

- Prompt placeholders supported in templates:
  - `{{CONVERSATION_MEMORY}}` injects all validated top-level keys from the conversation's memory (keys derived from `ConversationMemoryData`).
  - `{{CONVERSATION_MEMORY__main_topics__action}}` injects only the specified validated keys.
  - `{{USER_PERSONA}}` injects all validated top-level keys from the user persona (keys derived from `UserPersonaData`, currently only `persona`).
  - `{{USER_PERSONA__persona}}` injects the specified validated keys.
  - Missing data renders as `[Not available]`.

## Message flow (updated)

```mermaid
graph TD
    A[User sends message] --> B[POST /api/conversations/{id}/messages]
    B --> C[DB save user message]
    C --> D{Queue mode?}
    D -- yes --> E[SQS send]
    D -- dev local --> F[Brain HTTP /query]
    E --> G[Brain Lambda]
    F --> H[Brain processes]
    G --> H
    H --> I[Brain HTTP callback -> /api/internal/brain_response]
    I --> J[DB save AI message + pipeline]
    J --> K[Client polls /api/messages/{user_message_id}/response]
```

## Environment variables (selected)

- Backend: `APP_ENV`, `PORT`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `AWS_REGION`, `SQS_QUEUE_URL`, `LOCAL_BRAIN_ENDPOINT_URL`, `FRONTEND_URL`, `S3_WEBSITE_URL`, `ALLOW_ALL_ORIGINS`.
- Brain: `BACKEND_CALLBACK_BASE_URL`, `BACKEND_CALLBACK_ROUTE`, `FLOW_CONFIG_S3_BUCKET_NAME`, `FLOW_CONFIG_S3_KEY`.

## Known gaps and notes

- TODO (pending): Implement persona read endpoint `GET /api/internal/users/{user_id}/persona` in the backend `internal` router. It should return `{ "persona_data": <json> }` (404 if none). Brain currently tolerates 404.
- Frontend uses `Authorization: Bearer <user_id>`; consider JWT in production.
- Lock down RDS Security Group ingress in production; Terraform notes TODO.

# Non-Technical Product Overview

This document provides a non-technical overview of the Curiosity Coach project, intended for a product manager or other non-technical stakeholders.

## Product Vision

The Curiosity Coach is an AI-powered learning companion that helps students explore their interests and develop critical thinking skills. Instead of just providing answers, the Curiosity Coach engages students in a conversation, asks thought-provoking questions, and encourages them to think for themselves.

### User Flow Diagram

```mermaid
graph TD
    A["User Logs In"] --> B{"Start new or continue?"};
    B -- "Start New" --> C["Starts New Conversation"];
    B -- "Continue" --> D["Selects Existing Conversation"];
    C --> E["Asks a Question"];
    D --> E;
    E --> F["Backend sends to Brain"];
    F --> G["Brain generates guiding question/response"];
    G --> H["Backend sends response to Frontend"];
    H --> I["User sees Coach's response"];
    I --> J{"Engages in Dialogue"};
    J -- "Responds" --> E;
    J -- "Ends Convo" --> K["Conversation is Saved"];
    subgraph "Review"
        L["User can review past conversations at any time"]
    end
    A --> L;
    K --> L;
```

## User Flow

The primary user flow is a conversation with the Curiosity Coach. Here's a typical scenario:

1.  **Login:** A student logs in to the application using their phone number.
2.  **Start a Conversation:** The student starts a new conversation or continues an existing one.
3.  **Ask a Question:** The student asks a question about a topic they are interested in.
4.  **Engage in a Dialogue:** The Curiosity Coach responds not with a direct answer, but with a question or a prompt to encourage the student to think more deeply about the topic. For example, if a student asks "Why is the sky blue?", the coach might respond with "That's a great question! What do you think makes the sky blue?".
5.  **Explore and Learn:** The conversation continues in this manner, with the coach guiding the student to discover the answer for themselves. The coach might provide analogies, examples, or break down complex topics into smaller pieces.
6.  **Conversation History:** All conversations are saved, so the student can review them later.

## Key Features

*   **Conversational Learning:** The core of the product is the conversational interface that promotes active learning.
*   **Personalized Experience:** The coach can adapt to the student's level of understanding and interests.
*   **Conversation Memory:** The system can summarize completed conversations to build a structured memory. This provides valuable insights into the student's learning journey and can be used to personalize future interactions.
*   **User Persona Generation:** The system analyzes a user's conversation memories to create a "persona," which is a summary of their interests, learning style, and preferences. This allows for an even more tailored and effective learning experience over time.
*   **User Feedback:** Users can provide direct feedback on their experience through a simple interface. They can give a "thumbs up" or "thumbs down" and optionally leave a text comment. This helps the development team understand user satisfaction and identify areas for improvement.
*   **Prompt and Version Management:** The system allows for sophisticated management of the prompts that guide the AI.
    *   **What are Prompts?** Prompts are the instructions and templates that the AI uses to generate its responses. We have different prompts for different tasks, such as the main conversational prompt or a prompt for summarizing conversations.
    *   **Versioning:** Instead of overwriting a prompt when we want to make a change, we create a new version. This gives us a complete history of all changes, allows us to test different wordings, and lets us switch between versions easily.
    *   **Editing and Creating Versions:** A special interface allows authorized users to edit the text of a prompt and save it as a new version.
    *   **Active vs. Production Versions:** The system supports both an "active" and a "production" version for a prompt. The "active" version is used for testing and development, allowing us to try out new ideas without affecting live users. The "production" version is the one that real users interact with, ensuring a stable and consistent experience. An administrator can designate a specific version as "production."
*   **Configurable "Brain":** The "Brain" of the coach is highly configurable. We can change its behavior by adjusting a `FlowConfig` file, allowing us to experiment with different conversational strategies without changing the code.

## How the Pieces Connect

1.  A student sends a message from the **Frontend** (the React app).
2.  The **Backend** (the FastAPI app) receives the message, saves it to the database, and sends it to the **Brain** service.
3.  The **Brain** service processes the message, using its prompts and configuration to decide on the best response.
4.  The **Brain** sends the response back to the **Backend**.
5.  The **Backend** saves the response to the database and sends it to the **Frontend**.
6.  The **Frontend** displays the response to the student.

This cycle continues for the entire conversation.

### Component Connection Diagram (Chat)

```mermaid
graph TD
    subgraph "User's Browser"
        User
    end

    subgraph "AWS Cloud"
        CloudFront
        S3_Frontend["S3 for Frontend"]
        Lambda_Backend["Backend Lambda (FastAPI + API Gateway)"]
        RDS["RDS (PostgreSQL)"]
        SQS["SQS Queue"]
        Lambda_Brain["Brain Lambda (Python)"]
        S3_Brain_Config["S3 for Brain Config"]
    end

    User -- "HTTPS Request" --> CloudFront;
    CloudFront -- "Serves React App" --> S3_Frontend;
    User -- "API Calls (Login, Chat)" --> Lambda_Backend;
    Lambda_Backend -- "CRUD Operations" --> RDS;
    Lambda_Backend -- "Enqueues Message" --> SQS;
    SQS -- "Triggers" --> Lambda_Brain;
    Lambda_Brain -- "Reads FlowConfig" --> S3_Brain_Config;
    Lambda_Brain -- "Fetches History & Persona" --> Lambda_Backend;
    Lambda_Brain -- "Posts Response" --> Lambda_Backend;
    Lambda_Backend -- "Sends response to User" --> User;
```

### Component Connection Diagram (Memory Generation)

In addition to the real-time chat flow, there is an asynchronous, manually-triggered process to create memories from conversations.

```mermaid
graph TD
    subgraph "Manual Trigger"
        A["Developer calls API endpoint"]
    end

    subgraph "Backend"
        B["Finds inactive conversations"]
        C["Sends list to SQS"]
    end

    subgraph "Brain"
        D["Picks up task from SQS"]
        E["Reads conversation history"]
        F["Generates summary (memory) with LLM"]
        G["Saves memory to database via Backend"]
    end
    
    A --> B;
    B --> C;
    C --> D;
    D --> E;
    E --> F;
    F --> G;
```

### Component Connection Diagram (User Persona Generation)

Similar to memory generation, there is an asynchronous, triggerable process to create user personas from their conversation memories.

```mermaid
graph TD
    subgraph "Manual or Automated Trigger"
        A["Developer or system calls API endpoint"]
    end

    subgraph "Backend"
        B["Finds users needing persona generation"]
        C["Sends list to SQS"]
    end

    subgraph "Brain"
        D["Picks up task from SQS"]
        E["Reads all of a user's conversation memories"]
        F["Generates user persona with LLM"]
        G["Saves persona to database via Backend"]
    end
    
    A --> B;
    B --> C;
    C --> D;
    D --> E;
    E --> F;
    F --> G;
```

This overview should provide a good understanding of the Curiosity Coach project from a product perspective.