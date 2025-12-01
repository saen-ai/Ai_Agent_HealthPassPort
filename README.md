# Health Passport Backend

A feature-based, scalable FastAPI backend for Health Passport application.

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB with Beanie ODM
- **Authentication**: JWT tokens with bcrypt password hashing
- **Email**: Gmail SMTP
- **Python**: 3.11+

## Project Structure

```
Backend_Health_passport/
├── app/
│   ├── core/               # Core infrastructure (security, email, etc.)
│   ├── features/           # Feature modules
│   │   ├── auth/          # ✅ Authentication (implemented)
│   │   ├── clinic/        # 🚧 Clinic management (todo)
│   │   ├── patients/      # 🚧 Patient management (todo)
│   │   ├── labs/          # 🚧 Lab results (todo)
│   │   └── ...            # Other features
│   ├── shared/            # Shared utilities
│   ├── middleware/        # Global middleware
│   ├── config.py          # Configuration
│   ├── database.py        # Database connection
│   └── main.py           # FastAPI application
├── tests/                 # Tests
├── scripts/              # Utility scripts
└── pyproject.toml        # Dependencies
```

## Setup

### 1. Prerequisites

- Python 3.11+
- MongoDB running on localhost:27017
- Gmail account with app password

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=health_passport

# Security
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
EMAIL_FROM=your-email@gmail.com

# Application
APP_NAME=Health Passport
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Environment
ENVIRONMENT=development
DEBUG=True
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Features

### ✅ Phase 1: Authentication (Completed)

- User signup with email/password
- User login with JWT tokens
- Forgot password flow with email
- Reset password with token
- Change password (authenticated)
- Get current user info

### 🚧 Future Features

- Clinic management
- Patient management
- Lab results
- Appointments
- Health programs
- Messaging/Chat
- Clinical notes
- Notifications
- AI features

## API Endpoints

### Authentication (`/api/v1/auth`)

- `POST /signup` - Register new user
- `POST /login` - Login user
- `POST /forgot-password` - Request password reset
- `POST /reset-password` - Reset password with token
- `POST /change-password` - Change password (auth required)
- `POST /logout` - Logout user (auth required)
- `GET /me` - Get current user info (auth required)

## Development

### Running Tests

```bash
pytest
```

### Code Style

```bash
# Format code
black app/

# Lint code
ruff check app/
```

## Architecture

### Feature-Based Structure

Each feature is self-contained with:
- `models.py` - Database models (Beanie documents)
- `schemas.py` - Request/Response schemas (Pydantic)
- `service.py` - Business logic
- `router.py` - API endpoints
- `dependencies.py` - Feature-specific dependencies

### Benefits

- **Scalable**: Easy to add new features
- **Maintainable**: Clear separation of concerns
- **Testable**: Features can be tested independently
- **Team-friendly**: Multiple developers can work on different features

## Contributing

1. Create a new feature folder in `app/features/`
2. Implement models, schemas, service, and router
3. Register router in `app/main.py`
4. Add tests in `tests/features/`

## License

Proprietary
