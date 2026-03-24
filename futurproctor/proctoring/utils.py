import os
import json
import requests
import time
from openai import OpenAI
from django.conf import settings

# Initialize OpenAI Client
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    api_key = api_key.strip()

client = OpenAI(api_key=api_key)

def generate_questions_openai():
    """
    Generates 30 MCQs and 2 Coding Questions using OpenAI API.
    Returns a dictionary with 'mcqs' and 'coding_questions'.
    """
    prompt = """
    Generate a JSON object for a technical interview exam with the following structure:
    {
      "mcqs": [
        {
          "question_text": "Question?",
          "options": ["A", "B", "C", "D"],
          "correct_option": "A",
          "category": "Aptitude"
        }
      ]
    }

    Requirements:
    1. EXACLTY 30 MCQs total: 15 Aptitude and Reasoning, 15 Technical (Python, DSA, DB, OOPS).
    2. Difficulty must be Medium, suitable for technical job screening.
    3. Ensure strictly valid JSON output.
    4. Do not include markdown formatting (like ```json ... ```), just the raw JSON string.
    5. Each MCQ object MUST have a "question_text" field.
    """

    models_to_try = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
    
    for model in models_to_try:
        try:
            print(f"Attempting question generation with model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a technical interview question generator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            
            content = response.choices[0].message.content
            print(f"Success with {model}!")
            return json.loads(content)
        except Exception as e:
            print(f"Failed with {model}: {e}")
            import traceback
            with open("generation_error.log", "a", encoding="utf-8") as f:
                f.write(f"--- Error with {model} ---\n")
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
            continue
            
    print("All models failed. Using Emergency Fallback.")
    
    # EMERGENCY FALLBACK: Return hardcoded questions so the exam never crashes.
    return {
        "mcqs": [
            {"question_text": "What is the time complexity of binary search?", "options": ["O(n)", "O(log n)", "O(n^2)", "O(1)"], "correct_option": "O(log n)", "category": "DSA"},
            {"question_text": "Which data structure is LIFO?", "options": ["Queue", "Stack", "Tree", "Graph"], "correct_option": "Stack", "category": "DSA"},
            {"question_text": "Python is...", "options": ["Compiled", "Interpreted", "Both", "None"], "correct_option": "Interpreted", "category": "Python"},
            {"question_text": "SQL stands for...", "options": ["Structured Query Language", "Simple Query List", "Standard Question List", "None"], "correct_option": "Structured Query Language", "category": "DB"},
            {"question_text": "To remove duplicates from a list in Python, convert it to...", "options": ["Tuple", "Set", "Dictionary", "String"], "correct_option": "Set", "category": "Python"},
            {"question_text": "Which sorting algorithm is fastest on average?", "options": ["Bubble Sort", "Quick Sort", "Insertion Sort", "Selection Sort"], "correct_option": "Quick Sort", "category": "DSA"},
            {"question_text": "What is 2 + 2?", "options": ["3", "4", "5", "6"], "correct_option": "4", "category": "General"},
            {"question_text": "Which is immutable in Python?", "options": ["List", "Dictionary", "Set", "Tuple"], "correct_option": "Tuple", "category": "Python"},
            {"question_text": "Select Option A", "options": ["Option A", "Option B", "Option C", "Option D"], "correct_option": "Option A", "category": "Test"},
            {"question_text": "Select Option B", "options": ["Option A", "Option B", "Option C", "Option D"], "correct_option": "Option B", "category": "Test"},
            # Repeat to fill list if needed
        ] * 3 # Ensure we have enough MCQs
    }

def execute_code_judge0(source_code, language_id, stdin=""):
    """
    Executes code using Judge0 RapidAPI.
    """
    url = f"https://{os.environ.get('JUDGE0_HOST')}/submissions?base64_encoded=false&wait=true"
    
    headers = {
        "x-rapidapi-key": os.environ.get("JUDGE0_API_KEY"),
        "x-rapidapi-host": os.environ.get("JUDGE0_HOST"),
        "Content-Type": "application/json"
    }
    
    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Error executing code: {e}")
        return {"error": str(e)}

# --- Round 2 AI Utilities ---

def transcribe_audio(audio_file):
    """
    Transcribes audio using OpenAI Whisper.
    audio_file: a Django FieldFile (e.g., InterviewQuestion.candidate_audio)
    """
    try:
        # Django FieldFile must be opened from disk for the Whisper API
        file_path = audio_file.path
        with open(file_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=f, 
                response_format="text"
            )
        return transcript
    except Exception as e:
        print(f"Whisper Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def text_to_speech(text, output_filename="response.mp3"):
    """
    Converts text to speech using OpenAI TTS-1 (fastest model).
    """
    try:
        response = client.audio.speech.create(
            model="tts-1",        # tts-1 is fastest (lower quality but fine for interview)
            voice="alloy",
            input=text,
            speed=1.05            # Slightly faster playback
        )
        
        save_path = os.path.join(settings.MEDIA_ROOT, 'interview_audio', 'ai')
        os.makedirs(save_path, exist_ok=True)
        
        filename = f"{int(time.time())}_{output_filename}"
        full_path = os.path.join(save_path, filename)
        response.stream_to_file(full_path)
        
        return f"interview_audio/ai/{filename}"
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def generate_ai_response(transcript, resume_text, history, skills):
    """
    Ultra-fast AI response using GPT-4o-mini with a minimal prompt.
    Only sends the last 3 Q&A exchanges for context (not the full history).
    """
    # Truncate resume to keep prompt tiny
    short_resume = (resume_text or "")[:500]
    
    # Only use last 6 messages (3 Q&A pairs) for context
    recent = history[-6:] if len(history) > 6 else history
    context_str = "\n".join([f"{'AI' if m['role']=='assistant' else 'Candidate'}: {m['content']}" for m in recent])

    prompt = f"""Skills: {skills}
Resume snippet: {short_resume}

Recent conversation:
{context_str}

Candidate just said: "{transcript}"

Score the answer (0-10 technical, communication, confidence) and ask the NEXT interview question.
Keep the next_question under 2 sentences. Be conversational.

Reply as JSON only:
{{"score_technical":N,"score_communication":N,"confidence_level":N,"feedback":"one line","next_question":"short question"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise technical interviewer. Reply in JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=250          # Force short responses
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"GPT Error: {e}")
        return {
            "score_technical": 5,
            "score_communication": 5,
            "confidence_level": 5,
            "feedback": "Good answer.",
            "next_question": "Can you tell me more about a challenging project you worked on?"
        }

def extract_resume_text(file):
    """
    Basic text extraction from PDF.
    """
    try:
        if file.name.endswith('.pdf'):
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text[:2000] # Limit context size
        return "Resume content placeholder (PDF parsing failed or non-PDF)."
    except ImportError:
        return "PyPDF2 not installed. Resume parsing disabled."
    except Exception as e:
        print(f"File Parse Error: {e}")
        return "Resume content could not be parsed."

def evaluate_code_openai(problem_description, constraints, sample_input, sample_output, hidden_test_cases, candidate_code, language):
    """
    Evaluates candidate code using OpenAI GPT-4o.
    """
    prompt = f"""
    You are a strict technical coding judge.
    
    PROBLEM:
    {problem_description}
    
    CONSTRAINTS:
    {constraints}
    
    SAMPLE I/O:
    Input: {sample_input}
    Output: {sample_output}
    
    HIDDEN TEST CASES:
    {json.dumps(hidden_test_cases)}
    
    CANDIDATE CODE ({language}):
    {candidate_code}
    
    TASK:
    1. Simulate the execution of the candidate's code against the sample cases and hidden test cases.
    2. Determine if it is correct.
    3. Calculate Time and Space Complexity.
    4. Provide constructive feedback.
    
    RETURN JSON ONLY:
    {{
        "passed": boolean,
        "score": integer (0 to 10),
        "correct_testcases": integer,
        "total_testcases": integer,
        "feedback": "string",
        "time_complexity": "string",
        "space_complexity": "string"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a code evaluation engine. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Evaluation Error: {e}")
        return {
            "passed": False,
            "score": 0,
            "correct_testcases": 0,
            "total_testcases": len(hidden_test_cases) + 1,
            "feedback": f"Evaluation failed due to system error: {str(e)}",
            "time_complexity": "Unknown",
            "space_complexity": "Unknown"
        }
