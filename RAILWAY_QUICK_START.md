# 🚀 Railway Quick Start Guide

## Quick Deployment Steps

### 1. Backend Deployment

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your repository
3. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Generate domain → Copy URL (e.g., `https://your-api.up.railway.app`)

### 2. Frontend Deployment

1. In same project → New Service → GitHub Repo
2. **Start Command**: `streamlit run app/frontend.py --server.port $PORT --server.address 0.0.0.0`
3. **Environment Variable**: 
   - Key: `API_URL`
   - Value: `https://your-api.up.railway.app` (from step 1)
4. Generate domain → Copy URL

### 3. Update Backend CORS

In `app/main.py`, update CORS to include your frontend URL:

```python
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
```

Or set environment variable in Railway:
- Key: `ALLOWED_ORIGINS`
- Value: `https://your-frontend.up.railway.app,http://localhost:8501`

### 4. Test

- Backend: Visit `https://your-api.up.railway.app/health`
- Frontend: Visit `https://your-frontend.up.railway.app`
- API Docs: Visit `https://your-api.up.railway.app/docs`

---

## Environment Variables Reference

### Backend Service:
- `PORT` - Auto-set by Railway (don't change)
- `ALLOWED_ORIGINS` - Comma-separated list of allowed origins (optional)

### Frontend Service:
- `PORT` - Auto-set by Railway (don't change)
- `API_URL` - Your backend API URL (required)

---

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)

