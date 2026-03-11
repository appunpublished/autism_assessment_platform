# PythonAnywhere Deployment Guide

## 1) Upload code
Use either git clone on PythonAnywhere, or upload a zip.

Project path example:
`/home/<your-username>/autism_assessment_platform`

## 2) Create virtualenv and install requirements
```bash
cd /home/<your-username>/autism_assessment_platform
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Set production environment variables
In Bash console:
```bash
echo 'export DJANGO_SECRET_KEY="<set-a-long-random-secret>"' >> ~/.bashrc
echo 'export DJANGO_DEBUG="False"' >> ~/.bashrc
echo 'export DJANGO_ALLOWED_HOSTS="<your-username>.pythonanywhere.com"' >> ~/.bashrc
echo 'export DJANGO_CSRF_TRUSTED_ORIGINS="https://<your-username>.pythonanywhere.com"' >> ~/.bashrc
source ~/.bashrc
```

## 4) Run migrations and collect static
```bash
cd /home/<your-username>/autism_assessment_platform
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

## 5) Configure Web App in PythonAnywhere
From the **Web** tab:
- Create a new web app (manual config, Python 3.11)
- Set **Source code** to:
  `/home/<your-username>/autism_assessment_platform`
- Set **Working directory** to:
  `/home/<your-username>/autism_assessment_platform`
- Set **Virtualenv** to:
  `/home/<your-username>/autism_assessment_platform/venv`

### WSGI file
Edit WSGI file to:
```python
import os
import sys

path = "/home/<your-username>/autism_assessment_platform"
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autism_platform.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Static files mapping
In Web tab -> Static files:
- URL: `/static/`
- Directory: `/home/<your-username>/autism_assessment_platform/staticfiles`

## 6) Reload app
Press **Reload** in Web tab.

## 7) Smoke test
Open:
- `https://<your-username>.pythonanywhere.com/`
- `https://<your-username>.pythonanywhere.com/api/questions/`
