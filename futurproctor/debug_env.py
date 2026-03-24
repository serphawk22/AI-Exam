import os
import django
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv()

print("File: debug_env.py is running")

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')
django.setup()

from proctoring.utils import generate_questions_openai

print(f"OPENAI_API_KEY set: {bool(os.environ.get('OPENAI_API_KEY'))}")
if os.environ.get('OPENAI_API_KEY'):
    print(f"Key starts with: {os.environ.get('OPENAI_API_KEY')[:5]}...")

print("\nTesting Question Generation...")
try:
    data = generate_questions_openai()
    if data:
        print("Success! Questions generated.")
        print(f"MCQs: {len(data.get('mcqs', []))}")
        print(f"Coding: {len(data.get('coding_questions', []))}")
    else:
        print("Failed: No data returned from generate_questions_openai (returned None).")
except Exception as e:
    print(f"Error during generation: {e}")
