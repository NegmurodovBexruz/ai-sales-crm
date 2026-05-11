# AI Sales CRM

AI Sales CRM is a full-stack AI-powered sales automation platform for small businesses that sell through Telegram.

The system combines:

- FastAPI backend
- PostgreSQL/Supabase database
- Telegram bot
- AI customer support
- Product catalog
- Cart-based multi-item ordering
- Operator handoff
- Business owner/admin dashboard
- Operator dashboard
- Super admin dashboard

The goal is to help small businesses automate customer support, product Q&A, order collection, stock tracking, and operator notifications.

---

## Main Features

### AI Customer Support

The Telegram bot answers customer questions using:

- business profile
- uploaded `.docx` business knowledge
- product catalog
- stock information
- discount prices
- conversation history

The AI is instructed not to invent:

- prices
- stock availability
- delivery rules
- return policy
- product details

If the AI cannot answer confidently, it routes the customer to a human operator.

---

### Multi-language Telegram Bot

The customer selects language after `/start`:

- Uzbek Latin
- Uzbek Cyrillic
- Russian

After language selection, bot messages, buttons, validation errors, and order flow messages must follow the selected language.

---

### Cart-Based Order Flow

Orders are created through a cart-like Telegram flow.

Customer can:

- choose category
- choose product
- enter quantity
- add multiple products
- view cart
- edit product quantity
- remove product from cart
- cancel order
- confirm final order

A single order can contain multiple products through `order_items`.

Stock is not decreased when the order is created.  
Stock decreases only when the order is marked as `done`.

---

### Business Knowledge Upload

Business owner/admin can upload a `.docx` file containing business information:

- delivery policy
- return policy
- payment rules
- working hours
- support instructions

The backend extracts text from the document and stores it as business knowledge for AI replies.

---

### Product Management

Products include:

- name
- description
- category
- price
- optional discount price
- stock count
- image URL
- tags

Availability is calculated from `stock_count`:

| Stock count | Status |
|---:|---|
| 0 | out_of_stock |
| 1–10 | low_stock |
| >10 | active |

Discount price is optional. If `discount_price` exists, the UI shows the original price crossed out and the discount price next to it.

---

### Operator Handoff

If AI cannot answer:

1. The system checks whether the customer has username or phone number.
2. If contact data exists, operators are notified immediately.
3. If not, the bot asks the customer to share phone number.
4. After phone is shared, the pending operator request is sent to operators.

Operators are managed from the dashboard, not from `.env`.

`TELEGRAM_ADMIN_CHAT_ID` is used only as fallback.

---

### Operator Dashboard

Operators can log in with:

- operator code
- Telegram chat ID

Operator dashboard is separate from owner/admin dashboard.

Operators can currently:

- view business products
- see stock status
- see prices
- see product availability

Operators cannot:

- edit products
- access business settings
- access members
- access super admin panel

---

### Super Admin Dashboard

Super admin is a global platform administrator.

Super admin can view:

- all businesses
- all users
- all business members
- all orders
- all operators
- global platform statistics

Super admin is not created from public signup.

---

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- PostgreSQL / Supabase
- JWT authentication
- aiogram 3.x
- python-docx
- OpenAI / Gemini-compatible AI provider

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- JWT-based auth
- Business dashboard
- Operator dashboard
- Super admin dashboard

### Infrastructure

- Supabase PostgreSQL
- Render for FastAPI backend
- Vercel for frontend
- Telegram Bot API
- Gemini/OpenAI for AI replies

---

## Project Structure

```text
ai-sales-crm/
  backend/
    app/
      api/
        routes/
      bot/
        handlers/
        states/
      core/
      db/
      models/
      schemas/
      services/
      utils/
      main.py
    alembic/
    requirements.txt
    .env.example

  frontend/
    app/
    components/
    lib/
    public/
    package.json
    .env.local.example

  scripts/
    run_bot_polling.py
    make_super_admin.py
    backfill_business_codes.py
    test_*.py
```

---

## Local Setup

Backend:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend uses only `NEXT_PUBLIC_API_URL` for the backend URL.

## Backend Env

Required or commonly used backend variables:

- `APP_ENV`
- `APP_DEBUG`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `AI_PROVIDER`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `TELEGRAM_ADMIN_CHAT_ID`
- `BACKEND_URL`
- `FRONTEND_URL`

Development-only fallback variables:

- `TELEGRAM_BOT_TOKEN`
- `DEFAULT_BUSINESS_ID`

Production Telegram webhooks use per-business bot tokens stored in the database and the route:

```text
POST /api/telegram/webhook/{public_business_id}
```

## Deployment

Render backend:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Python: 3.11.x

Vercel frontend:

- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: leave empty
- Set `NEXT_PUBLIC_API_URL` to the Render backend URL
