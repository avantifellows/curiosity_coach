1. add .env files
- curiosity_coach_frontend/.env.local
- backend/.env.local
- Brain/src/.env

2. run migrations for db
- make sure local pg db is running
- cd backend
- (if it doesnt exist, run: python3 -m venv venv)
- uv pip compile requirements.txt -o requirements.lock
- uv pip install -r requirements.lock
- alembic upgrade head

3. open 3 terminals

terminal 1:
cd curiosity_coach_frontend
npm install
npm run dev
- this runs on: localhost:3000

terminal 2:
cd backend
(if it doesnt exist, run: python3 -m venv venv)
./run.sh
- this runs on: localhost:5000

terminal 3:
cd Brain
(if it doesnt exist, run: python3 -m venv venv)
./run.sh
- this runs on: localhost:5001


4. Go to: http://localhost:3000/prompts and here you can edit visit 1,2,3 and steady state prompts. Make sure to set them as production once you set their new active versions.

5. To edit memory generation and user persona prompts, edit these files 
- Brain/src/prompts/user_persona_generation_prompt.txt
- Brain/src/prompts/memory_generation_prompt.txt

6. Make sure to change this in llm_config.json. Right now its set to gpt-4o-mini.
```json
"opening_message": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.8,
    "max_tokens": 500
}
```