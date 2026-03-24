## Installation & Setup
### Prerequisites
- Python 3.x
- Postgress SQL installed and running

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
