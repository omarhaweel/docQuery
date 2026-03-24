# Deploying DocQuery on Render

Follow these steps to host the **backend** and **frontend** on [Render](https://render.com).

---

## Prerequisites

- A [Render](https://render.com) account (free tier is fine).
- Your project in a **Git** repo (GitHub or GitLab) that Render can access.
- An **OpenAI API key** for the backend.

---

## Step 1: Deploy the backend (Web Service)

1. In the [Render Dashboard](https://dashboard.render.com), click **New** → **Web Service**.
2. **Connect your repository** (GitHub/GitLab) and select the `docQuery` repo.
3. Configure the service:
   - **Name:** e.g. `docquery-api` (you’ll use this in the frontend URL).
   - **Region:** Choose the one closest to you.
   - **Root Directory:** leave blank (repo root).
   - **Runtime:** **Docker**.
   - **Dockerfile Path:** `backend/Dockerfile`.
   - **Instance type:** Free (or paid if you need more resources).
4. **Environment:**
   - Add variable: `OPENAI_API_KEY` = your OpenAI API key (mark as **Secret**).
5. **Documents and vectorstore (important):**
   - The backend loads PDFs from `backend/Documents/` (or repo-root `Documents/`).
   - The FAISS index is stored under **`backend/vectorstore/`** when that folder exists (this matches the Docker image layout). Committing a prebuilt `backend/vectorstore` avoids re-embedding every deploy (much faster and more reliable on Render).
   - On Render’s free tier there is **no persistent disk**, so:
     - **Option A:** Put the PDFs you need inside the repo under `backend/Documents/`. They will be in the image and the vectorstore will be built on each deploy (slower first request after deploy).
     - **Option B:** Use a [Render Disk](https://render.com/docs/disks) (paid), mount it, and put `Documents` and `vectorstore` there; you’d need to adjust the backend to read from the mounted path.
   - For a simple first deploy, use **Option A**: add your PDFs under `backend/Documents/` and commit them (or use a few small test PDFs).
6. Click **Create Web Service**. Wait for the first build and deploy.
7. Copy your backend URL, e.g. `https://docquery-api.onrender.com` (no trailing slash). You’ll need it for the frontend.

### Debug if the frontend “doesn’t get a response”

- Open **`https://<your-backend>.onrender.com/health`** → should be `{"status":"ok"}` (service is up).
- Open **`https://<your-backend>.onrender.com/ready`** → should be `{"status":"ready"}`. If you get `503` with a `detail` message, that’s the real error (e.g. missing `OPENAI_API_KEY`, no PDFs, or pipeline crash).
- Ensure **`OPENAI_API_KEY`** is set on the **backend** service in Render (not only locally in `.env`).

---

## Step 2: Deploy the frontend (Web Service with Docker)

1. In the Render Dashboard, click **New** → **Web Service** again.
2. Select the **same repository** (`docQuery`).
3. Configure:
   - **Name:** e.g. `docquery-app`.
   - **Root Directory:** leave blank.
   - **Runtime:** **Docker**.
   - **Dockerfile Path:** `frontend/Dockerfile`.
4. **Environment (required) — runtime, not only build:**
   - Add: `BACKEND_URL` = your backend’s **public HTTPS** URL from Step 1, e.g. `https://docquery-api.onrender.com` (**no trailing slash**).
   - The frontend Docker image substitutes this when the **container starts**, so you can change it in the dashboard and redeploy without rebuilding from a wrong baked-in URL.
   - **Must be `https://`** if your frontend is served over HTTPS (mixed content: `http://` API from an `https://` page is blocked by the browser).
5. After changing `BACKEND_URL`, trigger a new deploy (or restart) so nginx picks up the value.
6. Click **Create Web Service**. Wait for the build and deploy.
7. Open the frontend URL (e.g. `https://docquery-app.onrender.com`) and test the chat; it should call your backend.

---

## Step 3: CORS (if needed)

The backend already enables CORS in `backend/interface.py`. If your frontend is on a different host (e.g. `docquery-app.onrender.com`) and you see CORS errors, ensure the backend allows that origin (e.g. `*` or your frontend URL). The current setup should work if CORS is set to allow all origins.

---

## Summary

| Service   | Type        | Dockerfile            | Env / build args                          |
|----------|-------------|------------------------|-------------------------------------------|
| Backend  | Web Service | `backend/Dockerfile`   | `OPENAI_API_KEY` (secret)                  |
| Frontend | Web Service | `frontend/Dockerfile`  | Build: `BACKEND_URL` = backend Render URL |

- **Backend URL** → set as `BACKEND_URL` when creating the frontend service.
- **Documents** → include PDFs in `backend/Documents/` in the repo for a simple deploy, or use a Render Disk for persistence.

After both services are live, use the **frontend** URL in the browser; the app will talk to the backend automatically.
