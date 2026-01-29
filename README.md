# Raffaello

Raffaello is a management system for the **Raffaello apartment complex**, which I manage for my family.  
It is designed to help administrators, residents, and accountants track contracts, charges, and payments in a clear and structured way.

---

## How to run the project

### 1. Clone the repository

```sh
git clone https://github.com/ignamartinoli/raffaello-backend.git
cd raffaello-backend
```

### 2. Configure environment variables

Create a `.env` file in the project root with the following variables:

```env
ENV=dev

# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/raffaello

# JWT Configuration
SECRET_KEY=your_jwt_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# First Admin User Credentials
FIRST_ADMIN_EMAIL=admin@example.com
FIRST_ADMIN_PASSWORD=change_me

# SMTP Configuration
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=onboarding@resend.dev

# RapidAPI Integration
RAPIDAPI_KEY=your_rapidapi_key

# Frontend URL
FRONTEND_URL=http://localhost:5173
```

> **Note**  
> If needed, I can provide temporary API keys for development purposes. Just send me an email.

### 3. Run the backend with Docker

```sh
docker compose up --build
```

### 4. Run the frontend

The frontend lives in a separate repository:

`https://github.com/ignamartinoli/raffaello-frontend`

Follow the instructions there to start the frontend locally.

---

## System overview

Raffaello is a role-based management system focused on the **financial operations of an apartment complex**.

### Roles and capabilities

**Administrator**
- Manage users and roles
- Create and manage apartments
- Manage contracts, charges, and payments

**Residents**
- View their apartment details
- Access contracts
- Track rental and tax-related financial status

**Accountant**
- View payment status across apartments
- Identify unpaid charges

---

## Assumptions and trade-offs

The domain is actually from my current experience managing an apartment complex, and automating the Excel spreadsheets used daily to reduce errors and time.

<img width="1432" height="274" alt="image" src="https://github.com/user-attachments/assets/8fa383ec-4328-4c46-998e-3e7abb3a8745" />

*An excerpt from a table from the 3 spreadsheets that we use, with information hidden for privacy purposes*

An example of a domain-specific constraint is that municipal, provincial, and water bills receive discounts in my province when they are paid on a regular basis.
If even a single apartment payment is late, all other apartments owned by the same person lose these discounts.
For this reason, owners typically charge tenants directly and pay these bills centrally, ensuring that discounts are applied consistently across all apartments.

---

## AI tools and IDE agents used

During development, I used several AI-assisted tools:

- **ChatGPT** – quick questions and conceptual clarification
- **ChatGPT Codex** – PR and repository reviews
- **GitHub Copilot** – inline coding assistance (via Cursor IDE) and agentic code
- **Junie** – AI assistant integrated in JetBrains products (used mainly in WebStorm)
- **Cursor Bugbot**

While developing I had to guide the agentic code and I had to frequently correct it on various things:

- It tried to use the deprecated `python-jose` package instead of `PyJWT`
- It tried to use nonexistent versions for the `bcrypt` and `render` libraries
- When creating the `docker-compose.yml`, when creating the database, instead of using the `healthcheck` to begin the database migration, it tried to create a `docker-entrypoint.sh` file
- It tended to put business logic in the Repository and Controller
- When creating `PUT` endpoints, it would not distinguish between not passing a value in the JSON body, and passing it with a `NULL` value
- It would allow negative money

---

## Documentation

### Database schema

Below is the database diagram illustrating the data model:

<img width="1483" height="796" alt="Database diagram" src="https://github.com/user-attachments/assets/9c5052b6-78d6-4912-9c4a-22f921e6922e" />
