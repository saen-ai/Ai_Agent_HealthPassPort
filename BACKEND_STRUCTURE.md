# Health Passport Backend - Structure & Implementation Guide

## Tech Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: MongoDB with Beanie ODM
- **Authentication**: JWT tokens + bcrypt password hashing
- **Email**: Gmail SMTP (aiosmtplib)

## Directory Structure

```
Backend_Health_passport/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Environment settings (pydantic-settings)
│   ├── database.py             # MongoDB connection & Beanie init
│   ├── dependencies.py         # Shared dependencies
│   │
│   ├── core/                   # Core utilities (reusable)
│   │   ├── __init__.py
│   │   ├── security.py         # JWT tokens, password hashing
│   │   ├── email.py            # Gmail SMTP email service
│   │   ├── storage.py          # File storage (TODO)
│   │   ├── permissions.py      # RBAC (TODO)
│   │   ├── pagination.py       # Pagination utils (TODO)
│   │   └── filters.py          # Query filters (TODO)
│   │
│   ├── features/               # Feature modules
│   │   ├── __init__.py
│   │   │
│   │   ├── auth/               # ✅ IMPLEMENTED
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # User, PasswordReset (Beanie documents)
│   │   │   ├── schemas.py      # Pydantic request/response schemas
│   │   │   ├── service.py      # Business logic
│   │   │   ├── router.py       # API endpoints
│   │   │   └── dependencies.py # Auth middleware (get_current_user)
│   │   │
│   │   ├── clinic/             # 🚧 PLACEHOLDER
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # Basic Clinic model defined
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── patients/           # 🚧 PLACEHOLDER (empty files)
│   │   ├── labs/               # 🚧 PLACEHOLDER
│   │   ├── appointments/       # 🚧 PLACEHOLDER
│   │   ├── programs/           # 🚧 PLACEHOLDER
│   │   ├── messages/           # 🚧 PLACEHOLDER
│   │   ├── notes/              # 🚧 PLACEHOLDER
│   │   ├── notifications/      # 🚧 PLACEHOLDER
│   │   ├── ai/                 # 🚧 PLACEHOLDER
│   │   └── files/              # 🚧 PLACEHOLDER
│   │
│   ├── shared/                 # Shared utilities
│   │   ├── __init__.py
│   │   ├── models.py           # BaseDocument, TimestampMixin
│   │   ├── schemas.py          # BaseResponse, ErrorResponse
│   │   ├── exceptions.py       # Custom HTTP exceptions
│   │   ├── responses.py        # (TODO)
│   │   └── utils.py            # (TODO)
│   │
│   └── middleware/             # Global middleware
│       ├── __init__.py
│       ├── auth.py             # (TODO)
│       ├── cors.py             # (TODO - configured in main.py)
│       ├── logging.py          # (TODO)
│       └── error_handler.py    # (TODO)
│
├── tests/                      # Tests (TODO)
│   ├── features/
│   │   └── auth/
│   ├── core/
│   └── conftest.py
│
├── scripts/                    # Utility scripts (TODO)
│   ├── init_db.py
│   └── seed_data.py
│
├── .env                        # Environment variables (CONFIGURED)
├── .env.example
├── .gitignore
├── pyproject.toml              # Dependencies
├── README.md
└── run_server.sh               # Quick start script
```

---

## ✅ IMPLEMENTED: Auth Feature

### Models (app/features/auth/models.py)

```python
class User(Document):
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    name: str
    phone: Optional[str]
    is_active: bool = True
    is_verified: bool = False
    role: str = "admin"
    clinic_id: Optional[str]
    created_at: datetime
    updated_at: datetime

class PasswordReset(Document):
    user_id: str
    email: EmailStr
    token: Indexed(str, unique=True)
    expires_at: datetime
    used: bool = False
```

### API Endpoints (app/features/auth/router.py)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /api/v1/auth/signup | Register new user | No |
| POST | /api/v1/auth/login | Login, get JWT | No |
| POST | /api/v1/auth/logout | Logout | Yes |
| POST | /api/v1/auth/forgot-password | Request reset email | No |
| POST | /api/v1/auth/reset-password | Reset with token | No |
| POST | /api/v1/auth/change-password | Change password | Yes |
| GET | /api/v1/auth/me | Get current user | Yes |

### Schemas (app/features/auth/schemas.py)

**Requests:**
- SignupRequest: name, email, password, clinic_name
- LoginRequest: email, password
- ForgotPasswordRequest: email
- ResetPasswordRequest: token, new_password
- ChangePasswordRequest: current_password, new_password

**Responses:**
- UserResponse: id, email, name, phone, role, clinic_id, is_active, is_verified, timestamps
- LoginResponse: access_token, token_type, user
- SignupResponse: access_token, token_type, user, clinic_id
- MessageResponse: message

---

## Environment Variables (.env)

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=health_passport

# Security
JWT_SECRET_KEY=<secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=saeedanwar@getsnippet.co
SMTP_PASSWORD=<app-password>
EMAIL_FROM=saeedanwar@getsnippet.co

# Application
APP_NAME=Health Passport
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
ENVIRONMENT=development
DEBUG=True
```

---

## How to Add a New Feature

1. **Create folder**: `app/features/<feature_name>/`

2. **Create files**:
   - `__init__.py`
   - `models.py` - Beanie Document classes
   - `schemas.py` - Pydantic request/response models
   - `service.py` - Business logic class
   - `router.py` - FastAPI router with endpoints
   - `dependencies.py` - (optional) feature-specific dependencies

3. **Register in database.py**:
   ```python
   from app.features.<feature_name>.models import YourModel
   
   await init_beanie(
       document_models=[User, PasswordReset, YourModel, ...]
   )
   ```

4. **Register router in main.py**:
   ```python
   from app.features.<feature_name>.router import router as feature_router
   
   app.include_router(feature_router, prefix=settings.API_V1_PREFIX)
   ```

---

## Running the Backend

```bash
cd "Backend_Health_passport "
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Dependencies (pyproject.toml)

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
beanie>=1.27.0
motor>=3.6.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.12
email-validator>=2.2.0
aiosmtplib>=3.0.2
```

---

## Next Features to Implement (Phase 2+)

1. **Clinic Feature**: CRUD for clinic settings, branding (logo, color)
2. **Patient Feature**: Patient records management
3. **Labs Feature**: Lab results management
4. **Appointments Feature**: Scheduling system
5. **Programs Feature**: Health programs
6. **Messages Feature**: Chat/messaging
7. **Notes Feature**: Clinical notes
8. **Notifications Feature**: Push/email notifications
9. **AI Feature**: AI-powered features
10. **Files Feature**: File upload/storage

Each follows the same pattern: models → schemas → service → router → register
