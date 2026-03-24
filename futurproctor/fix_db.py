import os
import django
from dotenv import load_dotenv
from pathlib import Path

# Load env correctly
env_path = Path('futurproctor') / '.env'
load_dotenv(dotenv_path=env_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')
django.setup()

from proctoring.models import ExamSession

print("Cleaning up empty sessions...")
sessions = ExamSession.objects.filter(is_active=True)
count = 0
for s in sessions:
    if s.mcqs.count() == 0 and s.coding_questions.count() == 0:
        print(f"Deleting empty session {s.id} for student {s.student.name}")
        s.delete()
        count += 1

print(f"Deleted {count} empty sessions.")
