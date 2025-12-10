from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    input="what is calculus?",
    reasoning={
        "effort": "low"
    },
    text={
        "verbosity": "medium"
    })

print(response.output_text)