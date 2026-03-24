import os
import django
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')

# Load .env explicitly
env_path = Path('.') / 'futurproctor' / '.env'
load_dotenv(dotenv_path=env_path)

try:
    django.setup()
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)

from proctoring.utils import generate_questions_openai
from django.conf import settings

print(f"DEBUG: Checking API Key...")
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OPENAI_API_KEY is missing from environment variables!")
else:
    print(f"DEBUG: API Key found (starts with {api_key[:8]}...)")

print("\nDEBUG: Calling generate_questions_openai()...")
try:
    result = generate_questions_openai()
    if result:
        print("\nSUCCESS: OpenAI returned data!")
        print(f"MCQs: {len(result.get('mcqs', []))}")
        print(f"Coding: {len(result.get('coding_questions', []))}")
        import json
        # Print first MCQ to verify structure
        if result.get('mcqs'):
            print("Sample MCQ:", json.dumps(result['mcqs'][0], indent=2))
    else:
        print("\nFAILURE: OpenAI returned None.")
except Exception as e:
    print(f"\nCRITICAL ERROR during generation: {e}")
    import traceback
    traceback.print_exc()
