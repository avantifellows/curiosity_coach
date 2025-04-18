# Curiosity Coach Chat App

A simple chatbot application built with Gradio and backed by a PostgreSQL database. The app features user authentication via phone number and persistent chat history.

## Features

- User login with phone number
- Chat interface with message history
- PostgreSQL database for storing users and messages
- Dummy LLM response system (to be replaced with a real LLM later)

## Setup

### Installation

You can use either `pip` with requirements.txt or `uv` with pyproject.toml:

#### Using pip:
```
pip install -r requirements.txt
```

#### Using uv (recommended for faster installation):
```
# Install uv if you don't have it
pip install uv

# Install dependencies with uv
uv pip install .
```

### Database Setup

1. Set up PostgreSQL database:
   - Create a database named `curiosity_coach`
   - Copy `.env.example` to `.env` and update with your database credentials

2. Run the application:
   ```
   python app.py
   ```

3. Open the app in your browser (typically at http://127.0.0.1:7860)

## Project Structure

- `app.py` - Main Gradio application
- `database.py` - Database connection and interaction functions
- `model.py` - Dummy LLM implementation
- `schema.sql` - Database schema
