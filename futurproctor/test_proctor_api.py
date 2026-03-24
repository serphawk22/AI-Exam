import sys
import os
import django
import base64
import numpy as np
import cv2

# Initialize Django environment
sys.path.append(r"c:\Users\varun\Downloads\AI interview (3)\AI interview\Ai interview\futurproctor")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "futurproctor.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from proctoring.models import Student, ExamSession
from proctoring.views import analyze_frame_api
import json

def test():
    # 1. Create a dummy test image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    base64Image = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
    
    # 2. Get the first student and exam session
    student = Student.objects.first()
    if not student:
        print("No student found.")
        return
    session = ExamSession.objects.filter(student=student).first()
    if not session:
        print("No session found.")
        return
        
    print(f"Testing with Student: {student.user.username}, Session ID: {session.id}")
    
    # 3. Create a fake request
    rf = RequestFactory()
    body = json.dumps({
        "session_id": session.id,
        "image": base64Image
    })
    
    request = rf.post('/analyze_frame_api/', body, content_type='application/json')
    request.user = student.user
    
    # 4. Call the view
    response = analyze_frame_api(request)
    print("Response status_code:", response.status_code)
    print("Response content:", response.content.decode('utf-8'))

if __name__ == "__main__":
    test()
