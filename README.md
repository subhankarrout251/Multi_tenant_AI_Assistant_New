# Multi-tenant AI Assistant

## Local setup

1. Create a Python virtual environment and install the authoritative backend dependencies:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.lock
   ```

2. Copy `backend/.env.example` to `backend/.env` and provide `GROQ_API_KEY`,
   `ADMIN_API_KEY`, and `SESSION_SECRET`. Never expose either admin value in
   frontend `VITE_*` configuration.

3. Start the API from `backend/`:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Start the React application:

   ```bash
   cd frontend/chat-widget
   npm install
   npm run dev
   ```

Visit `/upload` in the frontend and sign in with the server-side
`ADMIN_API_KEY`. The backend creates an HTTP-only signed admin session; the
key is not embedded in the compiled frontend.
