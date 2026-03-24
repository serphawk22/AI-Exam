# AI-Based Online Exam Proctoring System

## Overview

The **AI-Based Online Exam Proctoring System** is a cutting-edge proctoring solution that ensures the integrity of online examinations. It employs advanced artificial intelligence techniques, including face detection, object detection, gaze tracking, real-time browser activity monitoring, and audio analysis, to monitor and prevent fraudulent activities during exams. This system helps maintain fairness and credibility in remote examinations by providing automated invigilation and detailed reports.

## Features
- **Face Detection**: Identifies and verifies the student's face to ensure the registered candidate is taking the exam.
- **Object Detection**: Detects unauthorized objects such as smartphones, books, or other cheating materials.
- **Gaze Detection**: Monitors the candidate's eye movements to detect suspicious behavior, such as looking away from the screen frequently.
- **Real-Time Browser Activity Monitoring**: Tracks tab switches and alerts when the candidate navigates away from the exam interface.
- **Audio Analysis**: Captures and analyzes external sounds through an external microphone to detect conversations or background noises.
- **Comprehensive Reports**: Generates detailed reports on suspicious activities and rule violations for invigilators to review.
- **User Authentication**: Face matching and email/password authentication required only during student registration and login.
- **Intuitive User Interface**: A well-designed homepage with a modern layout, login and register buttons, and important notices.
- **No Offline Mode Support**: The system explicitly notifies users that offline mode is not supported to prevent exam manipulation.

## Tech Stack
- **Backend**: Django 5.1.5 (Python-based web framework)
- **Database**: PostgressSQL(for efficient data storage and retrieval)
- **Frontend**: HTML, CSS, JavaScript (with UI/UX inspired by provided images)
- **AI Models**: OpenCV, MediaPipe (for face and object detection), custom ML models
- **Authentication**: Django authentication system with face-matching capabilities
- **Deployment**: Hosted on a cloud platform with scalability in mind


### 📽️ Demo Video

Watch the demo here: [https://youtu.be/O8kfFmwkfOU](https://youtu.be/O8kfFmwkfOU)


## Installation & Setup
### Prerequisites
- Python 3.x
- Postgress SQL installed and running
- 

### Steps
1. **Clone the Repository**
   ```bash
   https://github.com/HelpRam/An-Inbrowser-Proctoring-System.git
   cd .\futurproctor\
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Database**
   - Ensure Postgress is running.
   - Configure database settings in `settings.py`.

5. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start the Development Server**
   ```bash
   python manage.py runserver
   ```
   The application will be accessible at `http://127.0.0.1:8000/`.

## Usage
- **Register/Login**: Users must authenticate via face matching and email/password verification.
- **Start Exam**: Once authenticated, users can begin their exam session.
- **Real-time Monitoring**: AI models will track face, gaze, and object detection throughout the session.
- **Violation Alerts**: The system automatically flags suspicious activities for review.
- **View Reports**: Instructors or administrators can access detailed reports post-exam.

## Future Enhancements
- **Live Human Proctoring Integration**
- **Voice Command Detection for Additional Security**
- **Mobile App for Enhanced Accessibility**
- **Multi-Exam Support with Custom Rules Configuration**

## Contributors
- **Ramdular Yadav** (Lead Developer)


## License
This project is licensed under the MIT License.

## Contact
For any inquiries or contributions, feel free to reach out to:
- **Email**: rammey115@gmail.com
- **Phone**: 9819936338

