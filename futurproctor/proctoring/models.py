# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import pytz
from django.core.files.base import ContentFile
from django.utils import timezone
import pytz
from datetime import datetime  

# Define Nepal Time Zone
NEPAL_TZ = pytz.timezone('Asia/Kathmandu')

# Helper function to get Nepal time
def get_nepal_time():
    return timezone.now().astimezone(NEPAL_TZ)

def get_nepal_time_str():
    return get_nepal_time().strftime('%Y-%m-%d %I:%M:%S %p %Z')

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student', null=True, blank=True)
    name = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='student_photos/')
    face_encoding = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(default=datetime.now())
    feedback = models.TextField(null=True, blank=True, max_length=1000)

    def __str__(self):
        return self.name

class Exam(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exams', null=True, blank=True)
    exam_name = models.CharField(max_length=255, default='Default Exam Name')
    total_questions = models.IntegerField(null=True, blank=True)
    correct_answers = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(default=datetime.now())
    status = models.CharField(
        max_length=50,
        choices=[('ongoing', 'Ongoing'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        default='ongoing'
    )
    percentage_score = models.FloatField(null=True, blank=True)

    def calculate_percentage(self):
        if self.total_questions and self.total_questions > 0:
            self.percentage_score = round((self.correct_answers / self.total_questions) * 100, 2)
        else:
            self.percentage_score = 0.0
        self.save()

    def __str__(self):
        return f"{self.exam_name} - {self.student.name}"

class CheatingEvent(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='cheating_events',  # Added related_name for easier reverse lookups
        blank=True,
        null=True
    )
    cheating_flag = models.BooleanField(default=False)
    event_type = models.CharField(max_length=50, blank=True, null=True)
    # Use a single timestamp field. Here we use Nepal time.
    timestamp = models.DateTimeField(default=datetime.now())
    detected_objects = models.JSONField(default=list)
    tab_switch_count = models.IntegerField(default=0)

class CheatingImage(models.Model):
    event = models.ForeignKey(CheatingEvent, on_delete=models.CASCADE, related_name='cheating_images')
    image = models.ImageField(upload_to='cheating_images/')
    timestamp = models.DateTimeField(default=datetime.now())

class CheatingAudio(models.Model):
    event = models.ForeignKey(CheatingEvent, on_delete=models.CASCADE, related_name='cheating_audios')
    audio = models.FileField(upload_to='cheating_audios/', blank=True, null=True)
    timestamp = models.DateTimeField(default=datetime.now())

# --- Round 1 Exam Models ---

class ExamSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score_mcq = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.id} - {self.student.name}"

class MCQQuestion(models.Model):
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='mcqs')
    question_text = models.TextField()
    options = models.JSONField()  # Store options as a list ["A", "B", "C", "D"]
    correct_option = models.CharField(max_length=500)  # Full option text from OpenAI
    category = models.CharField(max_length=100) # Aptitude, Technical, etc.
    selected_option = models.CharField(max_length=500, null=True, blank=True)

class ProctoringLog(models.Model):
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='logs')
    event_type = models.CharField(max_length=100) # tab_switch, fullscreen_exit, etc.
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)


# --- Round 2: AI Voice Interview Models ---

class InterviewSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='interview_sessions')
    skills = models.TextField() # "Python, Django, AWS"
    resume = models.FileField(upload_to='resumes/')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_score = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    question_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Interview {self.id} - {self.student.name}"

class InterviewQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    audio_url = models.FileField(upload_to='interview_audio/ai/', null=True, blank=True) # AI Voice
    candidate_audio = models.FileField(upload_to='interview_audio/candidate/', null=True, blank=True) # User Answer
    candidate_transcript = models.TextField(null=True, blank=True)
    score_technical = models.IntegerField(default=0)
    score_communication = models.IntegerField(default=0)
    confidence_level = models.IntegerField(default=0)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
