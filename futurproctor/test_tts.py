import os
import sys
import django
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), 'futurproctor', '.env')
load_dotenv(dotenv_path=env_path, override=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')
django.setup()

from proctoring.utils import text_to_speech

print("Testing TTS...")
url = text_to_speech("Hello, this is a test of the text to speech.")
print("Result URL:", url)
