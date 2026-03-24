import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

# Load .env explicitly
env_path = Path('.') / 'futurproctor' / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get('OPENAI_API_KEY')

if not api_key:
    print("ERROR: API Key not found in environment!")
    exit(1)

print(f"DEBUG: API Key found: {api_key[:5]}...{api_key[-5:]}")

client = OpenAI(api_key=api_key)

print("DEBUG: Sending request to OpenAI (gpt-4o-mini)...")
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, OpenAI is working!'"}
        ],
        max_tokens=20
    )
    print("\nSUCCESS: OpenAI Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"\nERROR: OpenAI API call failed: {e}")
