# AI Sales CRM Frontend

Next.js admin dashboard for the AI Sales CRM backend.

## Setup

```powershell
cd frontend
npm install
```

Create `.env.local`:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Run the development server:

```powershell
npm run dev
```

Open the URL printed by Next.js and log in with a backend user account.

## Manual Verification Notes

- Sign up: open `/signup`, submit full name, email, password, and matching confirm password. Successful signup redirects to `/login?created=1` and shows `Account created. Please log in.`
- Duplicate signup: submit the same email again and confirm the backend error is shown.
- Login: open `/login`, submit valid credentials, confirm the token is saved and the app redirects to `/dashboard`.
- Invalid login: submit a wrong password and confirm an error message is shown.
- Protected dashboard: clear local storage and open `/dashboard`; it should redirect to `/login`.
- Logout: click `Logout`; the token is cleared and the app returns to `/login`.
- Forgot password: open `/forgot-password`; it shows the placeholder message and does not call the backend.
