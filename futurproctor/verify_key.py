import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Path to the .env file
env_path = Path('.') / 'futurproctor' / '.env'

print(f"Checking file at: {env_path.resolve()}")

if not env_path.exists():
    print("ERROR: .env file NOT FOUND at expected location!")
    sys.exit(1)

# 1. Read Raw Bytes to check for BOM or hidden chars
with open(env_path, 'rb') as f:
    raw_content = f.read()
    print(f"Raw file content (repr): {repr(raw_content)}")

# 2. Load with python-dotenv
load_dotenv(dotenv_path=env_path, override=True)
api_key = os.environ.get('OPENAI_API_KEY')

if not api_key:
    print("ERROR: OPENAI_API_KEY not found after loading .env!")
    sys.exit(1)

print(f"Loaded Key Length: {len(api_key)}")
print(f"Key First 5: '{api_key[:5]}'")
print(f"Key Last 5:  '{api_key[-5:]}'")

# Check for whitespace
if api_key != api_key.strip():
    print("WARNING: Key has leading/trailing whitespace! (This might be the issue)")
    api_key = api_key.strip()

# 3. Test with OpenAI (Cleaned Key)
print("\nTesting cleaned key with OpenAI...")
from openai import OpenAI
try:
    client = OpenAI(api_key=api_key)
    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=5
    )
    print("SUCCESS: Key is valid!")
except Exception as e:
    print(f"FAILURE: Key rejected. Error: {e}")
