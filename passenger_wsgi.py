import sys, os

# Add your project directory to the sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Set the settings module (replace 'main' with your actual Django app/project name)
os.environ['DJANGO_SETTINGS_MODULE'] = 'tmsapplication.settings'

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
