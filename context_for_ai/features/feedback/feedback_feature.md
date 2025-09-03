# Feature: User Feedback

This document outlines the implementation plan for adding a user feedback feature to the Curiosity Coach application.

## 1. Overview

The goal is to allow users to provide feedback on their experience with the application. This involves a simple thumbs up/down rating and an optional text comment, submitted via a modal on the frontend.

## 2. Task Breakdown

Here is a list of tasks to be completed.

### Backend

- [x] **Database:** Create a new `user_feedback` table.
    -   `id`: Primary Key
    -   `user_id`: Foreign Key to `users.id`
    -   `thumbs_up`: Boolean (True for up, False for down)
    -   `feedback_text`: Text (nullable)
    -   `created_at`: Timestamp
- [x] **Model:** Add a `UserFeedback` model to `backend/src/models.py`.
- [x] **Migration:** Generate and apply an Alembic migration for the new table.
- [x] **API:** Create a new feedback module (`backend/src/feedback/`).
    -   **Schema:** Define `FeedbackCreate` and `FeedbackRead` Pydantic models in `schemas.py`.
    -   **Router:** Create a `POST /api/feedback/` endpoint in `router.py` to receive and save user feedback.
    -   **Main App:** Integrate the new feedback router into the main FastAPI application in `backend/src/main.py`.

### Frontend

- [x] **API Service:** Add a `submitFeedback` function in `curiosity-coach-frontend/src/services/api.ts` to call the new backend endpoint.
- [x] **Feedback Modal:** Create a new component `FeedbackModal.tsx` (`curiosity-coach-frontend/src/components/FeedbackModal.tsx`).
    -   The modal should have UI elements for:
        -   Thumbs up / Thumbs down selection.
        -   A text area for optional feedback.
        -   A "Submit" button.
        -   A "Close" or "Cancel" button.
- [x] **UI Integration:**
    -   Identify the component that contains the "Logged in as..." message (likely `ChatHeader.tsx`).
    -   Add a "Liked it? Give feedback" link or button.
    -   Manage the state to show/hide the `FeedbackModal` when the link is clicked.
    -   On successful submission, the modal should close automatically.

## 3. Implementation Steps

### Step 1: Backend Development

1.  **Modify `backend/src/models.py`**: Add the `UserFeedback` SQLAlchemy model.
2.  **Generate Migration**:
    ```bash
    cd backend
    source venv/bin/activate
    alembic revision --autogenerate -m "create user_feedback table"
    ```
3.  **Apply Migration**:
    ```bash
    alembic upgrade head
    ```
4.  **Create Feedback API**:
    -   Create the directory `backend/src/feedback`.
    -   Create `backend/src/feedback/schemas.py`.
    -   Create `backend/src/feedback/router.py`.
    -   Update `backend/src/main.py` to include the new router.

### Step 2: Frontend Development

1.  **Update API Service**: Add the `submitFeedback` function to `api.ts`.
2.  **Create Modal Component**: Build the `FeedbackModal.tsx` component with state management for the form inputs.
3.  **Integrate Modal**:
    -   Modify the header component to include the feedback trigger.
    -   Use React state (e.g., `useState`) to manage the modal's visibility.
    -   Pass the necessary props and callbacks to the modal. 