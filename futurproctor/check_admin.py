
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurproctor.settings')
django.setup()

# Import models AFTER setup
from django.contrib.auth.models import User

# Check for superusers
users = User.objects.filter(is_superuser=True)

if users.exists():
    print("Superusers found:")
    for user in users:
        print(f"Username: {user.username}, Email: {user.email}")
else:
    print("No superusers found.")
