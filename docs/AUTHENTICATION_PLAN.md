# Authentication Implementation Plan

## Overview
This document outlines the plan for implementing user authentication with JWT, login, registration, and password recovery.

## DECISIONS MADE ✅

1. **JWT Library**: PyJWT (instead of python-jose)
2. **Password Hashing**: bcrypt (via passlib[bcrypt])
3. **Default User Role**: All new users get "tenant" role by default
4. **Refresh Tokens**: Not implemented
5. **Email Service**: SMTP
6. **User Creation**: Only admin users can create new users
7. **Configuration**: SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES in .env file only

## 1. Database Schema & Migration

### Users Table
- **id**: Primary key (auto-increment integer)
- **email**: Unique, indexed, max 320 characters (RFC 5321 compliant)
- **password_hash**: Not null, stores bcrypt/argon2 hash
- **role_id**: Foreign key to roles table, not null

### Migration Strategy
- Create Alembic migration `002_create_users_table.py`
- Add foreign key constraint to roles table
- Add unique constraint on email
- Add indexes for performance

## 2. Model & Schema Structure

Following the existing pattern (Role model):
- **Model** (`app/db/models/user.py`): SQLAlchemy ORM model
- **Schema** (`app/schemas/user.py`): Pydantic models for:
  - `User` (response model, excludes password_hash)
  - `UserCreate` (registration)
  - `UserLogin` (login credentials)
  - `UserUpdate` (optional, for profile updates)
  - `PasswordResetRequest` (for password recovery)
  - `PasswordReset` (for password reset confirmation)

## 3. Repository Layer

Create `app/repositories/user.py` with functions:
- `get_user_by_email(db: Session, email: str) -> User | None`
- `get_user_by_id(db: Session, user_id: int) -> User | None`
- `create_user(db: Session, user_data: UserCreate) -> User`
- `update_user_password(db: Session, user_id: int, password_hash: str) -> User`

## 4. Security Implementation

### Password Hashing
**✅ DECISION: bcrypt**
- Using `passlib[bcrypt]` for password hashing
- Mature, widely used, built-in salt generation

### JWT Implementation
**✅ DECISION: PyJWT**
- Using `PyJWT` for JWT encoding/decoding
- `python-multipart` for form data (if using form-based login)

**Configuration (from .env file):**
- `SECRET_KEY`: For signing JWTs (required, no default)
- `ALGORITHM`: JWT algorithm (e.g., HS256, RS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time in minutes

**Token Structure:**
- Access token only (no refresh tokens)

## 5. Authentication Endpoints

### 5.1 User Creation (`POST /api/v1/users`) - **ADMIN ONLY**
- ✅ **Only admin users can create new users**
- Requires authentication (admin role check)
- Validate email format
- Check email uniqueness
- Hash password
- Create user with specified role_id (or default to "tenant" if not provided)
- Return user (without password)

**Note**: This replaces public registration. Only admins can create users.

### 5.2 Login (`POST /api/v1/auth/login`)
- Verify email/password
- Generate JWT access token
- Return token and user info

### 5.3 Password Recovery - **CRITICAL SECTION**

#### Option A: Token-Based Reset (Recommended)
**Flow:**
1. User requests reset → `POST /api/v1/auth/forgot-password`
2. Generate secure token (JWT or random token)
3. Store token hash + expiration in database or cache
4. Send email with reset link containing token
5. User clicks link → `POST /api/v1/auth/reset-password` with token + new password
6. Validate token, update password, invalidate token

**Database Changes:**
- Add `password_reset_token` (nullable, indexed)
- Add `password_reset_expires` (nullable, datetime)

**Pros:**
- Secure (tokens expire)
- Stateless (can use JWT)
- Standard approach

**Cons:**
- Requires email service
- Token storage needed

#### Option B: Separate Reset Tokens Table
**Flow:**
- Create `password_reset_tokens` table
- Store: user_id, token_hash, expires_at, used (boolean)
- Clean up expired tokens periodically

**Pros:**
- Better audit trail
- Can track multiple active tokens
- Easier to invalidate all tokens for a user

**Cons:**
- More complex
- Requires cleanup job

#### Option C: OTP-Based (One-Time Password)
**Flow:**
1. User requests reset
2. Generate 6-8 digit OTP
3. Store OTP hash + expiration (5-10 minutes)
4. Send OTP via email/SMS
5. User submits OTP + new password
6. Validate OTP, update password

**Pros:**
- No links needed
- Works well on mobile
- Shorter expiration

**Cons:**
- Requires SMS service (if using SMS)
- Less secure than tokens (shorter, numeric only)
- User must remember OTP

#### Option D: Magic Link (No Password Reset)
**Flow:**
1. User requests reset
2. Generate secure token
3. Send link that logs user in directly
4. User sets new password while authenticated

**Pros:**
- Simpler UX
- No password reset form needed

**Cons:**
- Less secure (link grants temporary access)
- Requires authenticated password change endpoint

**Recommendation**: **Option A (Token-Based)** with JWT tokens stored in database with expiration. This is the most standard and secure approach.

### 5.4 Additional Endpoints
- `GET /api/v1/auth/me`: Get current user info (requires authentication)
- `POST /api/v1/users`: Create new user (admin only)
- `GET /api/v1/users`: List all users (admin only, optional)
- `GET /api/v1/users/{user_id}`: Get user by ID (admin only, optional)
- `PUT /api/v1/users/{user_id}`: Update user (admin only, optional)
- `DELETE /api/v1/users/{user_id}`: Delete user (admin only, optional)

## 6. Dependencies & Configuration

### New Dependencies
```txt
passlib[bcrypt]==1.7.4
PyJWT==2.8.0
python-multipart==0.0.9
email-validator==2.2.0
aiosmtplib==3.0.1  # or smtplib (standard library)
```

### Configuration Updates
Add to `app/core/config.py` (all from .env file):
- `SECRET_KEY`: str (required, no default)
- `ALGORITHM`: str (required, e.g., "HS256")
- `ACCESS_TOKEN_EXPIRE_MINUTES`: int (required)
- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`: int = 60 (optional, can have default)
- `RESEND_API_KEY`: str (required for email)
- `RESEND_FROM_EMAIL`: str (required for email, sender address)

## 7. Email Service (For Password Recovery)

### ✅ DECISION: Resend
- Using `resend` Python SDK for email sending
- Configure Resend API key in settings (.env file)
- Send plain text or HTML emails
- Resend settings: API_KEY, FROM_EMAIL

## 8. Middleware & Dependencies

### Authentication Dependency
Create `app/api/deps.py` function:
```python
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # Verify JWT, return user
```

### Role-Based Access Control
Create role checking dependencies:
```python
def require_role(required_role: str):
    # Check if user has required role
```

## 9. File Structure

```
app/
├── db/
│   └── models/
│       └── user.py          # NEW
├── schemas/
│   └── user.py              # NEW
├── repositories/
│   └── user.py              # NEW
├── services/
│   └── auth.py              # NEW (JWT, password hashing logic)
│   └── email.py             # NEW (email sending, optional)
├── core/
│   └── security.py          # UPDATE (add JWT functions)
│   └── config.py            # UPDATE (add auth settings)
└── api/
    └── routers/
        └── auth.py          # UPDATE (add all auth endpoints)
```

## 10. Implementation Order

1. ✅ Database migration (users table)
2. ✅ User model & schema
3. ✅ User repository
4. ✅ Security utilities (password hashing, JWT)
5. ✅ Registration endpoint
6. ✅ Login endpoint
7. ✅ Authentication dependencies (get_current_user)
8. ✅ Password recovery (chosen approach)
9. ✅ Email service (if needed)
10. ✅ Tests

## 11. Security Considerations

- **Password Requirements**: Enforce strong passwords (min length, complexity)
- **Rate Limiting**: Limit login/registration attempts (prevent brute force)
- **HTTPS Only**: JWT tokens should only be sent over HTTPS in production
- **Token Storage**: Client-side (httpOnly cookies preferred over localStorage)
- **CSRF Protection**: If using cookies, implement CSRF tokens
- **Email Verification**: Consider adding email verification for new registrations

## 12. Testing Strategy

- Unit tests for password hashing
- Unit tests for JWT generation/verification
- Integration tests for auth endpoints
- Test password recovery flow
- Test invalid tokens, expired tokens
- Test role-based access

---

## 13. First Admin User Creation

**Problem**: Only admin users can create users, but we need an admin user to start with.

### Options for Creating First Admin User:

#### Option 1: Alembic Migration Script (Recommended)
- Add a data migration that creates the first admin user
- Use a default password (from .env or hardcoded)
- Hash password using bcrypt
- Pros: Automatic, part of migration history
- Cons: Password in migration (but hashed)

#### Option 2: CLI Command
- Create a management command: `python -m app.cli create-admin`
- Prompt for email and password, or use .env defaults
- Pros: More flexible, can be run anytime
- Cons: Requires CLI infrastructure

#### Option 3: Manual SQL/Database Script
- Provide SQL script or manual instructions
- Pros: Simple, explicit
- Cons: Not automated, easy to forget

#### Option 4: Environment-Based Auto-Creation
- Check on startup if admin exists
- If not, create from env vars (FIRST_ADMIN_EMAIL, FIRST_ADMIN_PASSWORD)
- Pros: Automatic, no manual steps
- Cons: Runs on every startup (need to check if exists)

**Recommendation**: **Option 1 (Migration)** + **Option 2 (CLI)** for flexibility.

---

## ✅ FINAL DECISIONS

1. **Password Recovery**: ✅ Token-based reset (Option A) - JWT token in email link
2. **First Admin User**: ✅ Created during Alembic migration
3. **First Admin Details**: 
   - Name: "admin"
   - Email: From `.env` file (`FIRST_ADMIN_EMAIL`)
   - Password: From `.env` file (`FIRST_ADMIN_PASSWORD`)
4. **Password Requirements**: ✅ 
   - Minimum 8 characters
   - At least one uppercase letter
   - At least one lowercase letter
   - At least one number
   - At least one symbol
5. **SMTP Configuration**: ✅ Will be configured (guidance provided)
6. **Email Verification**: ✅ Not required (admin creates users)
7. **Rate Limiting**: ✅ Skipped for now
8. **User Management**: ✅ CRUD endpoints will be created later (only create endpoint for now)

---

## 14. SMTP Configuration Guide

### Required Environment Variables (add to `.env`):
```env
# JWT Configuration
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# First Admin User
FIRST_ADMIN_EMAIL=admin@example.com
FIRST_ADMIN_PASSWORD=YourSecurePassword123!

# Resend Configuration
RESEND_API_KEY=re_xxxxxxxxxxxxx  # Get from https://resend.com/api-keys
RESEND_FROM_EMAIL=noreply@yourdomain.com  # Must be a verified domain in Resend
```

### Resend Setup:

1. **Create a Resend account** at https://resend.com
2. **Get your API key** from https://resend.com/api-keys
3. **Verify your domain** in Resend dashboard (required for sending emails)
4. **Set FROM_EMAIL** to an email address using your verified domain (e.g., `noreply@yourdomain.com`)
- Enable 2FA first, then generate app password

**Outlook/Office365:**
- Host: `smtp.office365.com`
- Port: `587` (TLS)

**SendGrid:**
- Host: `smtp.sendgrid.net`
- Port: `587` (TLS)
- User: `apikey`
- Password: Your SendGrid API key

**Custom SMTP:**
- Get details from your email provider
- Usually port 587 (TLS) or 465 (SSL)

---

## 15. Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Update `requirements.txt` with new dependencies
- [ ] Update `app/core/config.py` with all settings
- [ ] Create Alembic migration for users table
- [ ] Add password reset token fields to users table (in migration)
- [ ] Create first admin user in migration

### Phase 2: Models & Schemas
- [ ] Create `app/db/models/user.py` (User model)
- [ ] Create `app/schemas/user.py` (Pydantic schemas)
- [ ] Update `app/db/models/__init__.py` to export User

### Phase 3: Security & Utilities
- [ ] Update `app/core/security.py` with:
  - Password hashing (bcrypt)
  - Password validation (requirements check)
  - JWT token creation
  - JWT token verification
  - Password reset token generation

### Phase 4: Repository Layer
- [ ] Create `app/repositories/user.py` with:
  - `get_user_by_email()`
  - `get_user_by_id()`
  - `create_user()`
  - `update_user_password()`
  - `set_password_reset_token()`
  - `get_user_by_reset_token()`
  - `clear_password_reset_token()`

### Phase 5: Email Service
- [ ] Create `app/services/email.py` with:
  - SMTP connection setup
  - Send password reset email function
  - Email template for password reset

### Phase 6: API Dependencies
- [ ] Update `app/api/deps.py` with:
  - `get_current_user()` (JWT verification)
  - `require_admin()` (role check)

### Phase 7: API Endpoints
- [ ] Update `app/api/routers/auth.py` with:
  - `POST /api/v1/auth/login` - Login endpoint
  - `POST /api/v1/auth/forgot-password` - Request password reset
  - `POST /api/v1/auth/reset-password` - Reset password with token
  - `GET /api/v1/auth/me` - Get current user
- [ ] Create `app/api/routers/users.py` with:
  - `POST /api/v1/users` - Create user (admin only)
- [ ] Update `app/api/v1/router.py` to include users router

### Phase 8: Testing
- [ ] Test password hashing
- [ ] Test JWT generation/verification
- [ ] Test login endpoint
- [ ] Test user creation (admin only)
- [ ] Test password reset flow
- [ ] Test password validation

---

## Ready for Implementation! ✅

All decisions have been made. The plan is complete and ready for implementation.
