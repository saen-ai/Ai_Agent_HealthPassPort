# AI Agent Context - Health Passport Backend

## Quick Summary
FastAPI backend with MongoDB (Beanie ODM) for a B2B health clinic management platform.

## What's Done (Phase 1)
- ✅ Auth system: signup, login, logout, forgot/reset password
- ✅ JWT authentication with bcrypt password hashing
- ✅ Gmail SMTP email service
- ✅ Feature-based project structure
- ✅ All placeholder folders for future features

## What's NOT Done Yet
- 🚧 Clinic management (settings, branding)
- 🚧 Patient management
- 🚧 Labs, Appointments, Programs, Messages, Notes, Notifications, AI

## Key Files
- `app/main.py` - FastAPI app entry
- `app/config.py` - Settings from .env
- `app/database.py` - MongoDB/Beanie connection
- `app/features/auth/` - Complete auth implementation
- `app/features/<other>/` - Placeholders ready

## Pattern for New Features
1. Create in `app/features/<name>/`
2. Files: models.py, schemas.py, service.py, router.py
3. Register model in `database.py`
4. Register router in `main.py`

## Commands
```bash
cd "Backend_Health_passport "
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Tech Stack
- FastAPI + Uvicorn
- MongoDB + Beanie ODM
- Pydantic v2
- JWT (python-jose) + bcrypt
- aiosmtplib (Gmail)

## PRD Location
See `PRD.txt` for full requirements.

