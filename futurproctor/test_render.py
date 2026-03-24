import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')
django.setup()

from django.test.client import Client
from django.contrib.auth.models import User
from proctoring.models import Student, ExamSession

try:
    c = Client()
    user = User.objects.first()
    if user:
        c.force_login(user)
        # Test result page
        response = c.get('/result/')
        print("Result Page Status:", response.status_code)
        
        # Test report page
        student_id = user.student.id
        response2 = c.get(f'/report_page/{student_id}/')
        print("Report Page Status:", response2.status_code)
    else:
        print("No users found.")
except Exception as e:
    traceback.print_exc()

