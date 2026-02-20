# Chat App

A real-time one-to-one chat application built with Django and Django Channels. Users can register, log in, and exchange messages instantly using WebSockets. Features include online/last-seen status, typing indicators, emoji picker, message deletion, and profile pictures.

---

## Requirements

- Python 3.10+
- pip

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd chat_app
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install django channels daphne pillow
```

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (optional, for admin access)

```bash
python manage.py createsuperuser
```

---

## Running the Project

```bash
python manage.py runserver
```

Open your browser and go to:

```
http://127.0.0.1:8000/
```

---

## Project Structure

```
chat_app/
├── accounts/        # Custom user model, registration, login, logout, profile
├── chat/            # Messaging views, WebSocket consumer, models, templates
├── core/            # Django project settings, ASGI config, root URLs
├── static/          # CSS, JS, and image assets
├── media/           # Uploaded profile pictures
├── manage.py
└── db.sqlite3
```

---

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/auth/register/` | Register a new account |
| `/auth/login/` | Log in |
| `/auth/logout/` | Log out |
| `/chat/users/` | View all users to start a chat |
| `/chat/chat/<user_id>/` | Open a chat with a specific user |
| `/admin/` | Django admin panel |

---

## Notes

- The channel layer uses `InMemoryChannelLayer`, which is suitable for development. For production, switch to a Redis-backed channel layer.
- `DEBUG = True` and the secret key are set for development only. Change both before deploying to production.
- SQLite is used as the database. For production, switch to PostgreSQL or another robust database.