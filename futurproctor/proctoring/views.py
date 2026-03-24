# Django Core Imports
from django.shortcuts import render, redirect, get_object_or_404  # Rendering templates, redirecting, and fetching objects
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, HttpResponseRedirect  # Handling HTTP responses
from django.contrib import messages  # Displaying success/error messages
from django.contrib.auth.decorators import login_required, user_passes_test  # Restricting views to logged-in users
from django.contrib.auth.models import User  # Accessing Django's built-in User model
from django.contrib.auth.hashers import make_password  # Hashing passwords securely
from django.contrib.auth import authenticate, login as auth_login  # Handling user authentication
from django.urls import reverse  # Generating dynamic URLs
from django.views.decorators.csrf import csrf_exempt  # Disabling CSRF protection for certain views (Use cautiously)
from django.utils.timezone import now  # Getting timezone-aware current time
from django.core.files.base import ContentFile  # Handling in-memory file storage
from django.conf import settings
import cv2
import io
from PIL import Image


# Models
from .models import Student, Exam, CheatingEvent, CheatingImage, CheatingAudio  # Importing custom models

# External Library Imports
import os  # Operating system utilities (e.g., file handling)
import json  # JSON handling (e.g., parsing request data)
import threading  # Running concurrent tasks (e.g., real-time monitoring)
import base64  # Encoding and decoding base64 (used for image handling)
import numpy as np  # Numerical operations, especially for image processing
import cv2  # OpenCV for computer vision tasks (e.g., face recognition)
import logging  # Logging errors and system activity
import time  # Time-based operations (e.g., timestamps)
from PIL import Image  # Image processing using the Pillow library
import io  # Handling in-memory file operations

# Machine Learning Imports (Custom AI Models for Proctoring)
from .ml_models.object_detection import detectObject  # Detecting objects in the exam environment
from .ml_models.audio_detection import audio_detection  # Detecting external sounds for cheating detection
from .ml_models.gaze_tracking import gaze_tracking # Tracking eye gaze to detect focus and distractions 



# from .ml_models.gaze_tracking import gaze_tracking  # Tracking eye gaze to detect focus and distractions
from .utils import (
    generate_questions_openai, execute_code_judge0, evaluate_code_openai,
    transcribe_audio, text_to_speech, generate_ai_response, extract_resume_text
)
from .models import ExamSession, MCQQuestion, ProctoringLog, InterviewSession, InterviewQuestion

# Fix: Import face_recognition (Previously missing)
try:
    import face_recognition
except ImportError:
    face_recognition = None
    print("Warning: face_recognition not installed. Face features will be disabled.")

# Fix: Proper datetime handling for Nepal Time Zone (Asia/Kathmandu)
import pytz  # For timezone handling
from datetime import datetime  # Standard date and time handling

# Define Nepal Time Zone
NEPAL_TZ = pytz.timezone('Asia/Kathmandu')

# Function to get Nepal's current time
def get_nepal_time():
    """
    Returns the current time in Nepal's timezone.
    This ensures all timestamps are consistent with the local time.
    """
    return datetime.now(NEPAL_TZ)


# Home page view
def home(request):
    """
    Renders the home page of the application.
    This is the entry point for users visiting the site.
    """
    return render(request, 'home.html')  # Render the home page


# Registration View
def registration(request):
    """
    Handles user registration, including:
    - Capturing form data (name, address, email, password, and photo)
    - Decoding and processing a base64-encoded image
    - Extracting face encoding using face recognition
    - Creating a new User and Student instance
    - Handling errors and displaying messages
    """
    if request.method == 'POST':  # Check if form is submitted
        # Retrieve form data
        name = request.POST['name']
        address = request.POST['address']
        email = request.POST['email']
        password = request.POST['password']
        captured_photo = request.POST.get('photo_data')  # Base64 image data

        try:
            # Decode the base64 image (photo_data comes in "data:image/png;base64,ENCODED_DATA")
            img_data = base64.b64decode(captured_photo.split(',')[1])
            nparr = np.frombuffer(img_data, np.uint8)  # Convert to numpy array
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # Convert to OpenCV image

            # Extract face encoding from the image
            face_encoding = get_face_encoding(image)  # Function should return a list or None
            if face_encoding is None:  # No face detected
                messages.error(request, "No face detected. Please try again.")
                return redirect('registration')
        except Exception as e:
            messages.error(request, f"Error processing image: {e}")
            return redirect('registration')

        # Check if the email is already registered
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('registration')

        try:
            # Create a new User instance
            user = User.objects.create(
                username=email,  # Use email as username for uniqueness
                email=email,
                first_name=name.split(' ')[0],  # Extract first name
                last_name=' '.join(name.split(' ')[1:]) if ' ' in name else '',  # Extract last name if available
                password=make_password(password),  # Hash password for security
            )

            # Create a linked Student instance
            student = Student(
                user=user,
                name=name,
                address=address,
                email=email,
                photo=ContentFile(img_data, name=f"{name}_photo.jpg"),  # Save the uploaded image
                face_encoding=face_encoding.tolist(),  # Convert NumPy array to list
            )
            student.save()

            # Store user session data
            request.session['user_id'] = user.id
            request.session['user_name'] = user.first_name

            messages.success(request, "Registration successful!")
            return redirect('login')  # Redirect to login page
        except Exception as e:
            messages.error(request, f"Error creating user: {e}")
            return redirect('registration')

    return render(request, 'registration.html')  # Render the registration page


# Helper function to extract face encoding (OpenCV Fallback)
def get_face_encoding(image):
    """
    Extracts face features using OpenCV since dlib/face_recognition is unavailable.
    - Uses Haar Cascade for face detection.
    - Uses Color Histogram as a simple feature vector (Verification/Matching).
    """
    try:
        # Load Haar Cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            return None
            
        # Get the first face
        (x, y, w, h) = faces[0]
        face_roi = image[y:y+h, x:x+w]
        
        # Resize to fixed size for consistency
        face_roi = cv2.resize(face_roi, (100, 100))
        
        # Calculate standard deviation/histogram as encoding (Simple Heuristic for "Verification")
        # Note: This is NOT true recognition, but checks "is this roughly the same image structure/color distribution"
        # Ideally we'd use LBPHFaceRecognizer but that requires training.
        # For this fix, we'll return a flattened 128-element standard histogram representation to match dimensionality if possible,
        # or simplified.
        
        # Simplification: Use a color histogram (HSV)
        # We use 16 bins for Hue and 8 bins for Saturation to get 16*8 = 128 dimensions.
        # This matches the dimension of dlib's encoding, keeping storage requirement similar.
        hsv_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv_roi], [0, 1], None, [16, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        return hist.flatten() # Return flattened histogram as encoding (128 floats)
        
    except Exception as e:
        print(f"Error in OpenCV face encoding: {e}")
        return None

# Helper function to match face encodings
def match_face_encodings(captured_encoding, stored_encoding):
    """
    Matches two face encodings.
    """
    if captured_encoding is None or stored_encoding is None:
        return False
        
    try:
        # Ensure numpy arrays
        captured_encoding = np.array(captured_encoding, dtype=np.float32)
        stored_encoding = np.array(stored_encoding, dtype=np.float32)
        
        # Check if dimensions match (in case comparing old dlib encoding with new opencv one)
        if captured_encoding.shape != stored_encoding.shape:
             # Basic dimensional check - if sizes differ, we can't compare directly. 
             # Assume mismatch or fallback to True if strict security not required for this debug phase.
             # However, let's try to be safe.
             print("Warning: Encoding dimension mismatch. Returning False.")
             return False

        # Compare Histograms using Correlation (method=0)
        # Correlation: Higher is better (1.0 is perfect match)
        score = cv2.compareHist(captured_encoding, stored_encoding, cv2.HISTCMP_CORREL)
        
        print(f"Face Match Score: {score}")
        
        # Threshold for match (Tune this as needed, 0.5 is a generic starting point for correlation)
        return score > 0.5
        
    except Exception as e:
        print(f"Error in matching encodings: {e}")
        return False


#Login View
@csrf_exempt  # Allow POST requests without CSRF token (for simplicity, use proper CSRF handling in production)
def login(request):
    """
    Handles user login with email, password, and facial recognition.
    - Authenticates the user using email and password.
    - Compares the captured photo with the stored face encoding.
    - Logs the user in if all checks pass.
    - Returns JSON responses for success or failure.
    """
    if request.method == "POST":
        # Retrieve form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        captured_photo_data = request.POST.get('captured_photo')

        # Validate required fields
        if not email or not password or not captured_photo_data:
            return JsonResponse({"success": False, "error": "Missing email, password, or captured photo."})

        try:
            # Decode the base64 image (remove the "data:image/png;base64," prefix)
            captured_photo_data = captured_photo_data.split(',')[1]
            captured_photo = base64.b64decode(captured_photo_data)

            # Convert the image to a NumPy array and decode it using OpenCV
            nparr = np.frombuffer(captured_photo, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Extract face encoding from the captured image
            captured_encoding = get_face_encoding(image)
            if captured_encoding is None:
                return JsonResponse({"success": False, "error": "No face detected in the captured photo."})

            # Authenticate the user using email and password
            user = authenticate(request, username=email, password=password)
            if user is None:
                return JsonResponse({"success": False, "error": "Invalid email or password."})

            try:
                # Fetch the associated student record
                student = user.student
                stored_encoding = np.array(student.face_encoding)

                # Compare the captured face encoding with the stored encoding
                if match_face_encodings(captured_encoding, stored_encoding):
                    # Log the user in
                    auth_login(request, user)

                    # Store student data in the session for future use
                    request.session['student_id'] = student.id
                    request.session['student_name'] = student.name

                    # Return a success response with redirect URL and student name
                    return JsonResponse({
                        "success": True,
                        "redirect_url": "/dashboard/",
                        "student_name": student.name
                    })
                else:
                    return JsonResponse({"success": False, "error": "Face does not match our records."})

            except Student.DoesNotExist:
                return JsonResponse({"success": False, "error": "No student record associated with this account."})

        except Exception as e:
            # Handle any unexpected errors during the login process
            return JsonResponse({"success": False, "error": f"Error processing image: {str(e)}"})

    # Render the login page for GET requests
    return render(request, "login.html")

# Logout View 
def logout_view(request):
    """
    Handles user logout.
    - Clears all session data.
    - Displays a success message.
    - Redirects the user to the home page.
    """
    request.session.flush()  # Clear all session data
    messages.success(request, "You have been logged out.")  # Display a success message
    return redirect('home')  # Redirect to the home page

# Video feed generation for the webcam
def gen_frames():
    """
    Generates a live video feed from the webcam.
    - Captures frames from the webcam using OpenCV.
    - Encodes each frame as a JPEG image.
    - Yields the frames as a streaming response for real-time display in the browser.
    """
    camera = cv2.VideoCapture(0)  # Open the default webcam (index 0)
    if not camera.isOpened():  # Check if the webcam was successfully opened
        raise RuntimeError("Could not open webcam.")

    while True:
        success, frame = camera.read()  # Read a frame from the webcam
        if not success:
            break  # Exit the loop if the frame cannot be read

        # Encode the frame as a JPEG image
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()  # Convert the frame to bytes

        # Yield the frame as part of a streaming response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    # Release the webcam when the loop ends
    camera.release()


# Video feed view
def video_feed(request):
    """
    Streams the live video feed to the browser.
    - Uses the `gen_frames` generator to fetch frames from the webcam.
    - Returns a `StreamingHttpResponse` with the appropriate content type for real-time video streaming.
    """
    return StreamingHttpResponse(
        gen_frames(),  # Use the generator to stream frames
        content_type='multipart/x-mixed-replace; boundary=frame'  # Required for live video streaming
    )


# Stop video feed view
def stop_event(request):
    """
    Dummy endpoint for stopping the video feed.
    - Can be extended to handle cleanup or other actions when the video feed is stopped.
    - Returns a JSON response indicating success.
    """
    return JsonResponse({'status': 'success'})  # Simple response for stopping the video feed

#Dashboard View
@login_required
def dashboard(request):
    """
    Renders the dashboard page for authenticated users.
    - Retrieves the user's name from the session.
    - Displays personalized content on the dashboard.
    - Handles cases where the user is not logged in (defaults to 'Guest').
    """
    # Retrieve the user's name from the session (default to 'Guest' if not found)
    user_name = request.session.get('user_name', 'Guest')

    # Prepare context data to pass to the template
    context = {
        'user_name': user_name,  # Pass the user's name to the template
    }

    # Render the dashboard template with the context data
    return render(request, 'dashboard.html', context)



# -------------------------Video Detection Thread----------------------------------
from django.utils import timezone
import pytz

# Define Nepal Time Zone
NEPAL_TZ = pytz.timezone('Asia/Kathmandu')

# Helper function to get Nepal time
def get_nepal_time():
    return timezone.now().astimezone(NEPAL_TZ)

def get_nepal_time_str():
    return get_nepal_time().strftime('%Y-%m-%d %I:%M:%S %p %Z')


logger = logging.getLogger(__name__)

# Global variables for warnings and background processes
video_warning = None
audio_warning = None
last_audio_detected_time = time.time()
stop_event = threading.Event()  # To stop background threads

# Function to process each frame
def process_frame(frame, request):
    """Process a single frame for cheating detection."""
    global video_warning
    
    # Initialize parsed warning for this frame
    current_warning = None
    
    labels, processed_frame, person_count, detected_objects = detectObject(frame)
    if detected_objects:
        print(f"DEBUG: Detected Objects -> {detected_objects}")
    cheating_event = None

    # Check for cheating conditions using robust detected_objects list
    suspicious_objects = [obj for obj in detected_objects if obj in ["cell phone", "book"]]
    if suspicious_objects:
        current_warning = f"ALERT: {', '.join(suspicious_objects)} detected!"
        cheating_event, _ = CheatingEvent.objects.get_or_create(
            student=request.user.student,
            cheating_flag=True,
            event_type="object_detected"
        )
        save_cheating_event(frame, request, cheating_event, detected_objects)

    if person_count > 1:
        current_warning = "ALERT: Multiple persons detected!"
        cheating_event, _ = CheatingEvent.objects.get_or_create(
            student=request.user.student,
            cheating_flag=True,
            event_type="multiple_persons"
        )
        save_cheating_event(frame, request, cheating_event, detected_objects)

    gaze = gaze_tracking(frame)
    if gaze["gaze"] != "center":
        # Only set look away warning if no other more serious warning exists
        if not current_warning:
             current_warning = "ALERT: Candidate not looking at the screen!"
        
        cheating_event, _ = CheatingEvent.objects.get_or_create(
            student=request.user.student,
            cheating_flag=True,
            event_type="gaze_detected"
        )
        save_cheating_event(frame, request, cheating_event, detected_objects)
        
    # Update global video warning
    video_warning = current_warning

# Function to process audio
def process_audio(request):
    """Continuously process audio for cheating detection."""
    global last_audio_detected_time, audio_warning

    while not stop_event.is_set():  # Check if stop_event is triggered
        audio = audio_detection()
        if audio["audio_detected"]:
            audio_warning = "ALERT: Suspicious audio detected!"
            cheating_event, _ = CheatingEvent.objects.get_or_create(
                student=request.user.student,
                cheating_flag=True,
                event_type="audio_detected"
            )
            save_cheating_event(None, request, cheating_event, audio_data=audio["audio_data"])
            last_audio_detected_time = time.time()

        if time.time() - last_audio_detected_time > 5:
            audio_warning = None

        time.sleep(2)  # Avoid excessive CPU usage

    print("Audio processing stopped.")  # Debugging to confirm the thread exits



# Background processing for video
def background_processing(request):
    """Runs video processing in the background."""
    cap = cv2.VideoCapture(0)
    frame_count = 0

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % 2 == 0:
            process_frame(frame, request)
        
        frame_count += 1
        time.sleep(0.5)
    
    cap.release()


# Helper function to create a WAV file from raw audio bytes
import io
import wave

def create_wav_bytes(raw_audio, channels=1, sampwidth=2, framerate=48000):
    """
    Wrap raw PCM audio bytes with a WAV header.
    
    :param raw_audio: The raw audio bytes (concatenated frames)
    :param channels: Number of audio channels (1 for mono)
    :param sampwidth: Sample width in bytes (2 for 16-bit audio)
    :param framerate: Frame rate (sample rate)
    :return: Audio data in WAV format as bytes
    """
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(raw_audio)
    return wav_buffer.getvalue()

## Function to save cheating event
def save_cheating_event(frame, request, cheating_event, detected_objects=None, audio_data=None):
    """Save cheating event along with images and audio in the database."""
    try:
        
        # Save detected objects
        if detected_objects:
            cheating_event.detected_objects = detected_objects  # Save as JSON
            cheating_event.save()
        # Save up to 10 sample images per event
        if frame is not None and cheating_event.cheating_images.count() < 10:
            try:
                image_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image_io = io.BytesIO()
                image_pil.save(image_io, format="JPEG", quality=85)
                image_content = image_io.getvalue()
                
                cheating_image = CheatingImage(event=cheating_event)
                cheating_image.image.save(
                    f"cheating_{time.time()}.jpg", 
                    ContentFile(image_content), 
                    save=True
                )
            except Exception as e:
                logger.error(f"Error processing image: {e}")
        
        # Save audio data
        if audio_data:
            try:
                # Convert raw audio bytes to a proper WAV file bytes.
                wav_data = create_wav_bytes(audio_data, channels=1, sampwidth=2, framerate=48000)
                cheating_audio = CheatingAudio(event=cheating_event)
                cheating_audio.audio.save(
                    f"cheating_audio_{time.time()}.wav", 
                    ContentFile(wav_data), 
                    save=True
                )
            except Exception as e:
                logger.error(f"Error processing audio: {e}")

        logger.info(f"Cheating event saved for student {request.user.student.id}")
    
    except Exception as e:
        logger.error(f"Error saving cheating event: {e}")

## Exam Page View
@login_required
def exam(request):
    """Start the exam and initialize proctoring."""
    try:
        # Get the Student instance associated with the logged-in user
        student = request.user.student
    except Student.DoesNotExist:
        # Handle the case where the user does not have a linked Student instance
        return HttpResponse("Student profile not found. Please contact support.", status=404)

    # Get the tab switch count from the CheatingEvent model
    violations = CheatingEvent.objects.filter(student=student).first()
    tab_count = violations.tab_switch_count if violations else 0

    # Load exam questions from the JSON file
    try:
        with open("D://Futurproctor//futurproctor//proctoring//dummy_data//ai.json") as file:
            data = json.load(file)
        questions = data.get("questions", [])
    except FileNotFoundError:
        return HttpResponse("Error: Questions file not found!", status=404)
    except json.JSONDecodeError:
        return HttpResponse("Error: Failed to parse the questions file!", status=400)

    # Removed obsolete hardware polling threads that crashed webcams

    # Render the exam template with questions and tab count
    # Combine warnings for initial render
    initial_warning = video_warning or audio_warning
    return render(request, 'exam.html', {
        'questions': questions,
        'warning': initial_warning,
        'tab_count': tab_count,
    })

# Submit exam
@login_required
def submit_exam(request):
    if request.method == 'POST':
        # Stop the background threads
        global stop_event
        stop_event.set()
        user = request.user

        # Load questions from ai.json
        try:
            with open('D:\\Futurproctor\\futurproctor\\proctoring\\dummy_data\\ai.json', 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            return HttpResponse("Error: Questions file not found!", status=404)
        except json.JSONDecodeError:
            return HttpResponse("Error: Failed to parse the questions file!", status=400)

        questions = data.get('questions', [])
        total_questions = len(questions)
        correct_answers = 0

        # Check answers
        for question in questions:
            question_id = question['id']
            user_answer = request.POST.get(f'answer_{question_id}')
            if user_answer == question['correct_answer']:
                correct_answers += 1

        # Save exam result
        exam = Exam(
            student=user.student,
            total_questions=total_questions,
            correct_answers=correct_answers,
            timestamp=timezone.now()
        )
        exam.save()

        # Redirect to success page
        messages.success(request, 'You have successfully completed the exam!')
        return redirect('exam_submission_success')

    return HttpResponse("Invalid request method.", status=400)

# Tab switch tracking
stop_event = threading.Event()


# Set up logging
logger = logging.getLogger(__name__)

# Tab switch tracking View
@login_required
def record_tab_switch(request):
    if request.method == "POST":
        # Get the current student
        student = request.user.student
        logger.info(f"Student: {student}")

        # # Get the active exam for the student
        # active_exam = Exam.objects.filter(student=student, status='ongoing').first()
        # if not active_exam:
        #     logger.error("No active exam found for the student")
        #     return JsonResponse({"error": "No active exam found for the student"}, status=400)

        # logger.info(f"Active Exam: {active_exam}")

        # Get or create a CheatingEvent for the student and exam
        cheating_event, created = CheatingEvent.objects.get_or_create(
            student=student,
            # exam=active_exam,
            event_type='tab_switch',  # Specify the event type
            defaults={
                'cheating_flag': False,
                'tab_switch_count': 0,
            }
        )

        logger.info(f"Cheating Event: {cheating_event}, Created: {created}")

        # Increment the tab switch count
        cheating_event.tab_switch_count += 1
        logger.info(f"Updated Tab Switch Count: {cheating_event.tab_switch_count}")

        # Set cheating_flag based on tab_switch_count
        cheating_event.cheating_flag = cheating_event.tab_switch_count >= 1
        logger.info(f"Cheating Flag: {cheating_event.cheating_flag}")

        # Save the updated CheatingEvent
        cheating_event.save()
        logger.info("Cheating Event saved successfully")

        # If tab switches exceed 2 (i.e., 3rd switch), take action
        if cheating_event.tab_switch_count > 2:
            stop_event.set()  # Stop background threads (ensure stop_event is defined)
            logger.info("Tab switches exceeded 2, terminated from the exam")
            return JsonResponse({
                "status": "terminated",
                "message": "You have exceeded the allowed tab switches (Limit: 3). Your exam is terminated."
            }, status=200)
        # Return a JSON response with the updated count and flag
        return JsonResponse({
            "status": "updated",
            "count": cheating_event.tab_switch_count,
            "cheating_flag": cheating_event.cheating_flag,
            "message": f"Tab switch detected! Total switches: {cheating_event.tab_switch_count}"
        }, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


# Exam submission success page
def exam_submission_success(request):
    return render(request, 'exam_submission_success.html')

# Result page
@login_required
def result(request):
    user = request.user
    
    # Check for Round 1 Exam Session first
    try:
        session = ExamSession.objects.filter(student=user.student).latest('start_time')
        
        context = {
            'user_name': user.first_name or user.username,
            'student_id': user.student.id,
            'exam_type': 'Round 1 (Aptitude & Technical)',
            'score_mcq': session.score_mcq,
            'total_score': session.total_score,
            'passed': session.passed,
            'is_round1': True,
            'mcq_total': 30, # Approx (15+15)
            'max_total': 30
        }
        return render(request, 'result.html', context)
        
    except ExamSession.DoesNotExist:
        # Fallback to old Exam model
        try:
            exam = Exam.objects.filter(student=user.student).latest('timestamp')
            
            total_questions = exam.total_questions or 1
            correct_answers = exam.correct_answers or 0
            percentage = (correct_answers / total_questions) * 100

            context = {
                'user_name': user.first_name,
                'score': correct_answers,
                'total_questions': total_questions,
                'percentage': round(percentage, 2),
                'is_round1': False
            }
            return render(request, 'result.html', context)
            
        except Exam.DoesNotExist:
            return HttpResponse("No exam found for this user", status=404)



from django.http import JsonResponse

# Fetch warnings
@csrf_exempt
def get_warning(request):
    """Fetch real-time warnings for the exam page."""
    global video_warning, audio_warning
    
    # Priority: Video warning > Audio warning
    combined_warning = video_warning if video_warning else audio_warning
    
    return JsonResponse({'warning': combined_warning})

# Streaming notifications to the proctor
def proctor_notifications(request):
    """Stream real-time cheating events to the proctor."""
    def event_stream():
        while True:
            events = CheatingEvent.objects.filter(cheating_flag=True).order_by('-timestamp')[:5]
            if events:
                yield f"data: {json.dumps([str(event) for event in events])}\n\n"
            time.sleep(5)
    
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


## Logout
def logout(request):
    return render(request,'home.html')

# ----------------------Admin Plus Report Page ---------------------------------------

# Admin views
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Sum
from django.contrib.admin.views.decorators import staff_member_required
from .models import Student, Exam, CheatingEvent, CheatingImage, CheatingAudio
@staff_member_required(login_url='/admin/login/')
def admin_dashboard(request):
    # Fetch students with counts for exams and cheating events
    students = Student.objects.annotate(
        exam_count=Count('exams'),
        cheating_event_count=Count('cheating_events')
    ).prefetch_related('exams', 'cheating_events')
    
    # Calculate trust score and exam scores for each student
    for student in students:
        # Example: Trust score decreases 10 points per cheating event (with a floor of 0)
        student.trust_score = max(0, 100 - (student.cheating_event_count * 10))
        
        for exam in student.exams.all():
            if exam.total_questions and exam.total_questions > 0 and exam.percentage_score is None:
                exam.percentage_score = calculate_exam_score(exam)
                exam.save()
    
    context = {
        'students': students,
    }
    return render(request, 'admin_dashboard.html', context)

## exam score
def calculate_exam_score(exam):
    """Calculate the exam score as a percentage."""
    if exam.total_questions and exam.total_questions > 0:
        return round((exam.correct_answers / exam.total_questions) * 100, 2)
    return 0.0


## Helper Function for aggregated detected objects
import json

# ---------------------- Round 1 Exam Views ---------------------------------------

@login_required
def start_round1(request):
    """
    Starts the Round 1 Exam.
    - Checks for existing active session.
    - If none, generates questions via OpenAI and creates a session.
    - Renders the exam interface.
    """
    student = request.user.student
    
    # Check if student already has an active session
    session = ExamSession.objects.filter(student=student, is_active=True).first()
    
    # If session exists but has no questions, treat it as invalid (zombie) and regenerate
    if session and (session.mcqs.count() == 0):
        print(f"DEBUG: Found incomplete session {session.id} (MCQs: {session.mcqs.count()}). Deleting...")
        session.delete()
        session = None

    if not session:
        print("DEBUG: Creating new session...")
        session = ExamSession.objects.create(student=student)
        
        # Generate Questions
        print("DEBUG: Calling OpenAI...")
        questions_data = generate_questions_openai()
        
        if questions_data:
            print(f"DEBUG: OpenAI returned data. MCQs: {len(questions_data.get('mcqs', []))}")
            # Save MCQs
            for mcq in questions_data.get('mcqs', []):
                MCQQuestion.objects.create(
                    exam_session=session,
                    question_text=mcq.get('question_text', mcq.get('question', 'Default Question')),
                    options=mcq['options'],
                    correct_option=mcq['correct_option'],
                    category=mcq['category']
                )
        else:
            print("ERROR: OpenAI returned None. Deleting empty session.")
            session.delete()
            return HttpResponse("Error: Failed to generate questions. Please refresh to try again.")
    
    # Fetch questions for the template
    mcqs = session.mcqs.all()
    
    print(f"DEBUG: Rendering exam. Session {session.id}. MCQs: {mcqs.count()}")

    return render(request, 'round1_exam.html', {
        'session': session,
        'mcqs': mcqs,
        'student': student
    })



@csrf_exempt
@login_required
def submit_round1(request):
    """
    Handles final exam submission.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            mcq_answers = data.get('mcq_answers', {}) # {question_id: selected_option}
            coding_answers = data.get('coding_answers', []) # List of {question_id, code, language_id}
            
            session = get_object_or_404(ExamSession, id=session_id, student=request.user.student)
            
            # Calculate MCQ Score
            mcq_score = 0
            for q_id, selected in mcq_answers.items():
                question = MCQQuestion.objects.get(id=q_id)
                question.selected_option = selected
                question.save()
                if selected == question.correct_option:
                    mcq_score += 1
            
            session.score_mcq = mcq_score
            
            session.total_score = mcq_score
            session.passed = session.score_mcq >= 15  # Minimum 50% to pass out of 30
            session.is_active = False
            session.end_time = datetime.now()
            session.save()
            
            return JsonResponse({'success': True, 'redirect_url': '/result/'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'error': 'Invalid method'}, status=400)

@csrf_exempt
@login_required
def log_proctoring_event(request):
    """
    AJAX Endpoint to log proctoring violations.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            event_type = data.get('event_type')
            details = data.get('details')
            
            session = get_object_or_404(ExamSession, id=session_id)
            ProctoringLog.objects.create(
                exam_session=session,
                event_type=event_type,
                details=details
            )
            return JsonResponse({'status': 'logged'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)

    detected_objects_set = set()
    for event in cheating_events:
        # If detected_objects is not already a list, try converting it.
        objs = event.detected_objects
        if isinstance(objs, str):
            try:
                objs = json.loads(objs)
            except json.JSONDecodeError:
                objs = []
        # Now, objs should be a list so add each one to our set.
        if isinstance(objs, list):
            detected_objects_set.update(objs)
    return list(detected_objects_set)

### Report view
def report_page(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    exam = student.exams.first()  # Legacy Exam
    
    # Fetch Round 1 Session
    exam_session = ExamSession.objects.filter(student=student).last()
    
    cheating_events = CheatingEvent.objects.filter(student=student)

    # Aggregate detected objects as a list
    detected_objects_list = [obj for event in cheating_events if isinstance(event.detected_objects, list) for obj in event.detected_objects]
    # Deduplicate and sort if needed
    detected_objects_list = list(set(detected_objects_list))
    detected_objects_str = ", ".join(detected_objects_list) if detected_objects_list else "No objects detected"

    # Sum up tab switch count from events
    total_tab_switch_count = cheating_events.aggregate(total=Sum('tab_switch_count'))['total'] or 0

    # Audio files
    cheating_audios = CheatingAudio.objects.filter(event__student=student)
    audio_urls = [audio.audio.url for audio in cheating_audios if audio.audio]

    context = {
        'student': student,
        'exam': exam,
        'exam_session': exam_session,  # Pass the session

        'detected_objects': detected_objects_str,
        'total_tab_switch_count': total_tab_switch_count,
        # You can also add correct answer attempt and total questions:
        'correct_answers': exam.correct_answers if exam else None,
        'total_questions': exam.total_questions if exam else None,
        'cheating_status': any(
            event.event_type in ['object_detected', 'multiple_faces_detected', 'tab_switch']
            for event in cheating_events
        ),
        'cheating_images': [
            {
                'url': img.image.url,
                'event_type': img.event.event_type,
                'timestamp': img.timestamp
            }
            for img in CheatingImage.objects.filter(event__student=student)
        ],
        'audio_urls': audio_urls,
        'cheating_events': cheating_events,  # if you need to list them
    }
    return render(request, 'report_page.html', context)




from django.template.loader import get_template
from xhtml2pdf import pisa
# (Ensure you import any helper functions you might have, e.g., get_detected_objects_string)

def download_report(request, student_id):
    # Retrieve student and related data
    student = get_object_or_404(Student, id=student_id)
    exam = student.exams.first()  # Legacy
    
    # Fetch Round 1 Session
    exam_session = ExamSession.objects.filter(student=student).last()
    
    cheating_events = CheatingEvent.objects.filter(student=student)
    
    # Process detected objects inline
    detected_objects_list = [obj for event in cheating_events if isinstance(event.detected_objects, list) for obj in event.detected_objects]
    detected_objects_list = list(set(detected_objects_list))
    detected_objects_str = ", ".join(detected_objects_list) if detected_objects_list else "No objects detected"

    # Sum up tab switch counts
    total_tab_switch_count = cheating_events.aggregate(total=Sum('tab_switch_count'))['total'] or 0

    # Audio URLs (xhtml2pdf might need absolute paths for images and other media,
    # but for simple cases it often works fine)
    cheating_audios = CheatingAudio.objects.filter(event__student=student)
    audio_urls = [audio.audio.url for audio in cheating_audios if audio.audio]

    # Prepare context for the template
    context = {
        'student': student,
        'exam': exam,
        'exam_session': exam_session,  # Pass the session
        'detected_objects': detected_objects_str,
        'total_tab_switch_count': total_tab_switch_count,
        'correct_answers': exam.correct_answers if exam else None,
        'total_questions': exam.total_questions if exam else None,
        'cheating_status': any(
            event.event_type in ['object_detected', 'multiple_faces_detected', 'tab_switch']
            for event in cheating_events
        ),
        'cheating_images': [
            {
                'url': img.image.url,
                'event_type': img.event.event_type,
                'timestamp': img.timestamp
            }
            for img in CheatingImage.objects.filter(event__student=student)
        ],
        'audio_urls': audio_urls,
        'cheating_events': cheating_events,
    }
    
    # Render the HTML template with context
    template = get_template('report_page.html')
    html = template.render(context)

    # Create a HttpResponse with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{student.id}.pdf"'
    
    # Create PDF using xhtml2pdf (pisa)
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    # Check for errors
    if pisa_status.err:
        return HttpResponse('We had some errors while generating the PDF', status=500)
    
    return response


def add_question(request):
    return render(request, 'add_question.html')  # Ensure you have this template


# --- Round 2 Views ---

@login_required
def round2_intro(request):
    if request.method == 'POST':
        skills = request.POST.getlist('skills') # List of strings
        resume = request.FILES.get('resume')
        
        if not resume:
            return HttpResponse("Please upload a resume", status=400)
            
        # Ensure student profile exists
        try:
            student = request.user.student
        except Student.DoesNotExist:
            # Create if missing (though should exist from registration)
            student = Student.objects.create(
                user=request.user, 
                name=request.user.first_name or request.user.username, 
                email=request.user.email
            )

        # Create Session
        session = InterviewSession.objects.create(
            student=student,
            skills=", ".join(skills),
            resume=resume
        )
        
        # Redirect to the actual interview page (we will implement this next)
        return redirect('round2_interview_page', session_id=session.id)
        
    return render(request, 'round2_intro.html')

@login_required
def round2_interview_page(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    
    # If no questions exist, generate the first one (Introduction)
    if session.questions.count() == 0:
        first_question_text = f"Hello {session.student.name}, welcome to the second round of your interview. I see you are skilled in {session.skills}. Let's start with a brief introduction about yourself and your experience with these technologies."
        
        # Determine audio path
        audio_filename = f"q1_{session.id}.mp3"
        audio_url = text_to_speech(first_question_text, audio_filename)
        
        if not audio_url:
            return HttpResponse("Error: Failed to generate audio for question. Please try again.", status=500)
        
        InterviewQuestion.objects.create(
            session=session,
            question_text=first_question_text,
            audio_url=audio_url
        )
        session.question_count = 1
        session.save()

    return render(request, 'round2_interview.html', {'session': session})

@csrf_exempt
def round2_process_audio(request):
    """
    Accepts a transcript_text string from the Web Speech API (no Whisper needed).
    This makes the round-trip ultra fast: ~1s GPT-4o-mini + ~0.5s TTS.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        session_id = request.POST.get('session_id')
        audio_blob = request.FILES.get('audio_data')
        
        if not session_id or not audio_blob:
            return JsonResponse({'error': 'Missing audio data or session ID'}, status=400)
            
        session = InterviewSession.objects.get(id=session_id)
        current_question = session.questions.last()
        
        import time as _t
        t0 = _t.time()
        
        transcript_text = "No question found."
        if current_question:
            # Save Candidate Audio
            current_question.candidate_audio.save(f"ans_{current_question.id}.webm", audio_blob)
            current_question.save()
            
            # Transcribe with high-accuracy Whisper API
            transcript_text = transcribe_audio(current_question.candidate_audio)
            if not transcript_text:
                transcript_text = "(Unintelligible)"
            
            current_question.candidate_transcript = transcript_text
            current_question.save()
            
        t_whisper = _t.time()
        print(f"[PERF] Whisper Transcription: {t_whisper-t0:.2f}s")

        # End the interview after 10 questions
        if session.question_count >= 10:
            session.is_active = False
            session.save()
            return JsonResponse({
                'status': 'completed',
                'transcript': transcript_text,
                'message': 'Great interview! All questions answered. Generating your report now...'
            })

        t1 = _t.time()

        # Cache resume text in request session to avoid re-parsing PDF every call
        cache_key = f'resume_{session_id}'
        resume_text = request.session.get(cache_key)
        if not resume_text:
            resume_text = extract_resume_text(session.resume) or ""
            request.session[cache_key] = resume_text[:500]  # only keep 500 chars
            resume_text = request.session[cache_key]

        t2 = _t.time()
        print(f"[PERF] Resume: {t2-t1:.2f}s")

        # Build conversation history
        history = []
        for q in session.questions.all():
            history.append({"role": "assistant", "content": q.question_text})
            if q.candidate_transcript:
                history.append({"role": "user", "content": q.candidate_transcript})

        # Generate AI response
        ai_data = generate_ai_response(transcript_text, resume_text, history, session.skills)
        t2 = _t.time()
        print(f"[PERF] GPT: {t2-t1:.2f}s")

        # Store scores on current question
        if current_question:
            current_question.score_technical    = ai_data.get('score_technical', 0)
            current_question.score_communication = ai_data.get('score_communication', 0)
            current_question.confidence_level   = ai_data.get('confidence_level', 0)
            current_question.feedback           = ai_data.get('feedback', '')
            current_question.save()

        # Create audio for next question via TTS
        next_q_text    = ai_data.get('next_question', "Thank you. Let's move on to the next topic.")
        next_audio_url = text_to_speech(next_q_text, f"q{session.question_count + 1}_{session.id}.mp3")
        t3 = _t.time()
        print(f"[PERF] TTS: {t3-t2:.2f}s | TOTAL: {t3-t0:.2f}s")

        if not next_audio_url:
            next_audio_url = ''

        # Persist next question
        InterviewQuestion.objects.create(
            session=session,
            question_text=next_q_text,
            audio_url=next_audio_url if next_audio_url else None
        )
        session.question_count += 1
        session.save()

        audio_full_url = f"{settings.MEDIA_URL}{next_audio_url}" if next_audio_url else ''

        return JsonResponse({
            'status': 'success',
            'transcript': transcript_text,
            'next_question_text': next_q_text,
            'next_question_audio': audio_full_url
        })

    except InterviewSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        print(f"[round2_process_audio] ERROR: {e}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt
@login_required
def end_interview(request, session_id):
    """
    Called by the frontend when the 20-minute timer expires (or the user ends early).
    Marks the session as inactive, then uses GPT-4o-mini to generate a final analysis report.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    
    if not session.is_active:
        # Already ended — just redirect to the report
        return redirect('round2_report', session_id=session_id)
    
    # Mark session as ended
    session.is_active = False
    session.end_time = now()
    session.save()

    # Build a conversation history for GPT to analyse
    questions = session.questions.all()
    history = []
    for q in questions:
        history.append({"role": "assistant", "content": q.question_text})
        if q.candidate_transcript:
            history.append({"role": "user", "content": q.candidate_transcript})

    # Ask GPT for a final holistic report
    try:
        from .utils import client
        import json as _json
        prompt = f"""
You are an expert technical interviewer. Analyse the following interview between an AI and a candidate.
Candidate Skills: {session.skills}

Interview Transcript:
{_json.dumps(history, indent=2)}

Based on the above, provide:
1. An overall technical score (0-10)
2. An overall communication score (0-10)
3. An overall confidence score (0-10)
4. A FINAL overall score (0-10) — weighted: technical 50%, communication 30%, confidence 20%
5. A detailed 3-4 sentence summary of the candidate's performance
6. A list of 3 key strengths
7. A list of 3 areas for improvement

Return ONLY valid JSON in this EXACT format:
{{
    "score_technical": 0-10,
    "score_communication": 0-10,
    "score_confidence": 0-10,
    "overall_score": 0-10,
    "summary": "...",
    "strengths": ["...", "...", "..."],
    "improvements": ["...", "...", "..."]
}}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer providing a final evaluation."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5
        )
        report_data = _json.loads(response.choices[0].message.content)
        
        # Save overall score to session
        session.total_score = int(report_data.get('overall_score', 0))
        session.passed = session.total_score >= 6  # Pass threshold: 6/10
        session.save()
        
        # Store the report JSON in session's Django session (for display)
        request.session['interview_report'] = report_data
        request.session['interview_session_id'] = session_id
        
    except Exception as e:
        print(f"Report generation error: {e}")
        import traceback; traceback.print_exc()
        request.session['interview_report'] = None
        request.session['interview_session_id'] = session_id
    
    return redirect('round2_report', session_id=session_id)


@login_required
def round2_report(request, session_id):
    """
    Displays the final interview analysis report.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    questions = session.questions.all().order_by('created_at')
    
    # Try to retrieve cached report from session
    report_data = request.session.get('interview_report')
    
    # If no cached report, try to generate one on the fly (e.g., direct URL access)
    if not report_data:
        try:
            from .utils import client
            import json as _json
            history = []
            for q in questions:
                history.append({"role": "assistant", "content": q.question_text})
                if q.candidate_transcript:
                    history.append({"role": "user", "content": q.candidate_transcript})
            
            prompt = f"""
You are an expert technical interviewer. Briefly analyse this interview.
Candidate Skills: {session.skills}
Interview Transcript: {_json.dumps(history, indent=2)}

Return ONLY valid JSON:
{{
    "score_technical": 0-10,
    "score_communication": 0-10,
    "score_confidence": 0-10,
    "overall_score": 0-10,
    "summary": "...",
    "strengths": ["...", "...", "..."],
    "improvements": ["...", "...", "..."]
}}
"""
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            report_data = _json.loads(res.choices[0].message.content)
        except Exception as e:
            print(f"Report on-demand generation error: {e}")
            report_data = {
                "score_technical": session.total_score,
                "score_communication": session.total_score,
                "score_confidence": session.total_score,
                "overall_score": session.total_score,
                "summary": "Report could not be generated at this time.",
                "strengths": [],
                "improvements": []
            }
    
    context = {
        'session': session,
        'questions': questions,
        'report': report_data,
        'passed': session.passed,
    }
    return render(request, 'round2_report.html', context)

import base64
from django.core.files.base import ContentFile

@csrf_exempt
@login_required
def analyze_frame_api(request):
    """
    AJAX endpoint for web-native proctoring.
    Accepts a base64 encoded frame from the frontend, runs it through detectObject,
    logs cheating events, and returns any warnings.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        image_data = data.get('image', '')
        session_id = data.get('session_id')

        if not image_data or not session_id:
            return JsonResponse({'error': 'Missing image or session_id'}, status=400)

        # Decode base64 frame
        format, imgstr = image_data.split(';base64,') 
        ext = format.split('/')[-1]
        decoded_img = base64.b64decode(imgstr)

        # Convert to numpy array for OpenCV
        nparr = np.frombuffer(decoded_img, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return JsonResponse({'error': 'Failed to decode image'}, status=400)

        # Run model inference
        from .ml_models.object_detection import detectObject
        labels, processed_frame, person_count, detected_objects = detectObject(frame)
        
        current_warning = None
        session = get_object_or_404(ExamSession, id=session_id)
        
        # Check for multiple people
        if person_count > 1:
            current_warning = "Multiple persons detected!"
            cheating_event = CheatingEvent.objects.create(
                student=request.user.student,
                cheating_flag=True,
                event_type="multiple_persons"
            )
            if "multiple_persons" not in detected_objects: detected_objects.append("multiple_persons")
            save_cheating_event(frame, request, cheating_event, detected_objects)

        # Check for objects
        suspicious_objects = [obj for obj in detected_objects if obj in ["cell phone", "book"]]
        if suspicious_objects:
            current_warning = f"{', '.join(suspicious_objects).capitalize()} detected!"
            cheating_event = CheatingEvent.objects.create(
                student=request.user.student,
                cheating_flag=True,
                event_type="object_detected"
            )
            save_cheating_event(frame, request, cheating_event, detected_objects)

        return JsonResponse({
            'success': True,
            'warning': current_warning
        })

    except Exception as e:
        logger.error(f"Error in analyze_frame_api: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
