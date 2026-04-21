FitZone (Django)
=================

Overview
- FitZone is a Django web app for fitness memberships, trainer bookings, chat, and AI-driven nutrition recommendations.
- Key modules: login/register, membership, payments, trainer management, notifications, chat, fitness plans, AI chatbot, food recommendation system.

Tech Stack
- Django 5.2.4
- PostgreSQL
- Groq API for AI chatbot
- Khalti payment integration

Requirements
- Python 3.11+ (recommended)
- PostgreSQL server
- pip packages listed in requirements.txt

Quick Start
1) Create and activate a virtual environment
2) Install dependencies
   pip install -r requirements.txt
3) Create a .env file in this folder with required variables (see below)
4) Run migrations
   python manage.py migrate
5) Create admin user
   python manage.py createsuperuser
6) Run the server
   python manage.py runserver

Environment Variables (.env)
- DB_NAME=FitZone
- DB_USER=FitZone
- DB_PASSWORD=your_db_password
- DB_HOST=localhost
- DB_PORT=5432

- EMAIL_HOST_USER=your_email@example.com
- EMAIL_HOST_PASSWORD=your_email_app_password
- DEFAULT_FROM_EMAIL=your_email@example.com
- ADMIN_EMAIL=admin@example.com

- google_key=your_google_oauth_client_id
- GOOGLE_OAUTH_SECRET=your_google_oauth_client_secret

- GROQ_API_KEY=your_groq_api_key

- KHALTI_PUBLIC_KEY=your_khalti_public_key
- KHALTI_SECRET_KEY=your_khalti_secret_key

- SITE_URL=http://127.0.0.1:8000

Notes
- Uploaded files are stored under the media/ folder.
- Static files are served from static/ (and collected into staticfiles/ for deployment).
- If email sending fails in development, verify SMTP settings in .env.
