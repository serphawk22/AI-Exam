import os
import django
from dotenv import load_dotenv

# Load env correctly
from pathlib import Path
env_path = Path('futurproctor') / '.env'
load_dotenv(dotenv_path=env_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')
django.setup()

from proctoring.models import ExamSession, MCQQuestion, CodingQuestion

print("Checking Exam Sessions...")
sessions = ExamSession.objects.all()
for s in sessions:
    mcq_count = s.mcqs.count()
    coding_count = s.coding_questions.count()
    print(f"Session {s.id}: Student={s.student.name}, Active={s.is_active}, MCQs={mcq_count}, Coding={coding_count}")
    
    if s.is_active and mcq_count == 0:
        print(f"  -> WARNING: Session {s.id} is ACTIVE but EMPTY. This causes the issue!")
