# groq_test.py
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama3-70b-8192",  # or "llama3-70b-8192"
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain how list comprehensions work in Python."}
    ],
    temperature=0.2,
    max_tokens=300
)

print(response.choices[0].message.content)
