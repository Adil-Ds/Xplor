# Xplor Platform — Run Instructions

I have securely locked down the ports in the project code so they will not randomly interchange. 

- **Frontend Port**: Hardcoded to `5173`. `strictPort: true` is enabled in `vite.config.js`, meaning Vite will immediately crash and warn you if port 5173 is already in use (rather than silently switching to 3001 or 3002).
- **Backend Port**: Hardcoded to `8000` via `main.py` and `uvicorn`.

---

## 1. Start the Backend API

Open your first terminal window and run:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```
*This will strictly start the FastAPI backend on `http://localhost:8000`.*

## 2. Start the Frontend UI

Open a **new** terminal window and run:

```bash
cd frontend
npm run dev
```
*This will strictly start the Vite React frontend on `http://localhost:5173`.*

## 3. Start Local AI (Ollama)

Ollama runs silently as a background service on Windows, permanently bound to port `11434`. You do not need to run a server command for it. As long as the `qwen2.5` model is pulled, your backend will successfully communicate with it for the Data Chat features.

To access the platform, open your browser and navigate to:
👉 **http://localhost:5173**
