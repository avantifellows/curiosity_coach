# file: test_openai_env.py
import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    load_dotenv()  # loads variables from .env into environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in .env or environment")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello in one short sentence."}
        ],
        temperature=0.2,
        max_tokens=32,
    )
    print(resp.choices[0].message.content)

if __name__ == "__main__":
    main()