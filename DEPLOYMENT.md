# 🚀 Railway Deployment Guide

This guide will walk you through deploying the Smart Expense Categorizer to Railway.

## 📋 Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Account**: Your code should be in a GitHub repository
3. **Git Installed**: For local repository management

---

## 🎯 Deployment Options

You have **two options** for deployment:

### Option 1: Deploy as Two Separate Services (Recommended)
- **Backend Service**: FastAPI API
- **Frontend Service**: Streamlit App

### Option 2: Deploy as Single Service
- Combined deployment (not recommended for production)

---

## 📦 Option 1: Two Separate Services (Recommended)

### Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Verify these files exist**:
   - ✅ `requirements.txt`
   - ✅ `app/main.py` (Backend)
   - ✅ `app/frontend.py` (Frontend)
   - ✅ `Procfile` (optional, Railway can auto-detect)

### Step 2: Deploy Backend API

1. **Go to Railway Dashboard**: [railway.app/dashboard](https://railway.app/dashboard)

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure Backend Service**:
   - Railway will auto-detect it as a Python project
   - **Service Name**: `backend` or `api`
   - **Root Directory**: Leave as root (`.`)
   - **Build Command**: (Auto-detected, usually `pip install -r requirements.txt`)
   - **Start Command**: 
     ```
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

4. **Set Environment Variables** (if needed):
   - Go to Service → Variables
   - Add any custom environment variables
   - Railway automatically provides `$PORT`

5. **Generate Domain**:
   - Go to Service → Settings → Generate Domain
   - Copy the generated URL (e.g., `https://your-api.up.railway.app`)
   - **Save this URL** - you'll need it for the frontend!

### Step 3: Deploy Frontend

1. **Add New Service to Same Project**:
   - In your Railway project, click "New Service"
   - Select "GitHub Repo" → Choose the same repository

2. **Configure Frontend Service**:
   - **Service Name**: `frontend` or `web`
   - **Root Directory**: Leave as root (`.`)
   - **Build Command**: (Auto-detected)
   - **Start Command**:
     ```
     streamlit run app/frontend.py --server.port $PORT --server.address 0.0.0.0
     ```

3. **Set Environment Variables**:
   - Go to Service → Variables
   - Add: `API_URL` = `https://your-api.up.railway.app` (the backend URL from Step 2)
   - This tells the frontend where to find the API

4. **Generate Domain**:
   - Go to Service → Settings → Generate Domain
   - Copy the frontend URL (e.g., `https://your-frontend.up.railway.app`)

### Step 4: Update CORS Settings (Important!)

1. **Update Backend CORS**:
   - Edit `app/main.py`
   - Update the CORS middleware to allow your frontend domain:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://your-frontend.up.railway.app",
           "http://localhost:8501"  # For local testing
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
   - Commit and push the changes
   - Railway will auto-deploy

### Step 5: Verify Deployment

1. **Test Backend**:
   - Visit: `https://your-api.up.railway.app/health`
   - Should return: `{"status": "healthy", ...}`
   - Visit: `https://your-api.up.railway.app/docs`
   - Should show Swagger API documentation

2. **Test Frontend**:
   - Visit: `https://your-frontend.up.railway.app`
   - Should load the Streamlit app
   - Test the "🔌 Test Connection" button in the sidebar

---

## 📦 Option 2: Single Service Deployment

If you want to deploy everything in one service:

1. **Create New Project** in Railway
2. **Connect GitHub Repository**
3. **Set Start Command**:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. **Note**: This only runs the backend. To run both, you'd need a process manager like `supervisord` or run them in separate Railway services (Option 1 is better).

---

## 🔧 Configuration Files

### Procfile (Optional)
Railway can auto-detect Python apps, but you can create a `Procfile`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
frontend: streamlit run app/frontend.py --server.port $PORT --server.address 0.0.0.0
```

### railway.json (Optional)
For more control, create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

---

## 🌍 Environment Variables

### Backend Service Variables:
- `PORT` - Automatically set by Railway (don't set manually)
- Any custom variables your app needs

### Frontend Service Variables:
- `API_URL` - Your backend API URL (e.g., `https://your-api.up.railway.app`)
- `PORT` - Automatically set by Railway

---

## 🐛 Troubleshooting

### Issue: Build Fails
**Solution**: 
- Check `requirements.txt` is correct
- Ensure Python version is compatible (Railway uses Python 3.11+ by default)
- Check build logs in Railway dashboard

### Issue: Service Won't Start
**Solution**:
- Verify start command is correct
- Check that `$PORT` is used (Railway provides this)
- Ensure host is `0.0.0.0` (not `127.0.0.1`)

### Issue: Frontend Can't Connect to Backend
**Solution**:
- Verify `API_URL` environment variable is set correctly in frontend service
- Check CORS settings in backend allow your frontend domain
- Ensure backend is deployed and running

### Issue: Port Already in Use
**Solution**:
- Railway handles ports automatically via `$PORT`
- Don't hardcode port numbers

### Issue: Module Not Found Errors
**Solution**:
- Ensure all dependencies are in `requirements.txt`
- Check that imports use correct paths (relative vs absolute)

---

## 📊 Monitoring

1. **View Logs**: Railway Dashboard → Service → Deployments → View Logs
2. **Metrics**: Railway Dashboard → Service → Metrics
3. **Health Checks**: Use `/health` endpoint

---

## 🔄 Updating Deployment

1. **Push to GitHub**: 
   ```bash
   git add .
   git commit -m "Update deployment"
   git push
   ```

2. **Railway Auto-Deploys**: Railway automatically detects changes and redeploys

3. **Manual Deploy**: Railway Dashboard → Service → Deployments → Redeploy

---

## 💰 Railway Pricing

- **Free Tier**: $5 credit/month (usually enough for small projects)
- **Hobby Plan**: $20/month (for production use)
- Check [railway.app/pricing](https://railway.app/pricing) for current pricing

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Backend service created and deployed
- [ ] Backend domain generated and saved
- [ ] Frontend service created
- [ ] `API_URL` environment variable set in frontend
- [ ] Frontend domain generated
- [ ] CORS updated in backend to allow frontend domain
- [ ] Backend health check passes (`/health`)
- [ ] Frontend loads and can connect to backend
- [ ] Test file upload and categorization

---

## 🎉 Success!

Once deployed, you'll have:
- **Backend API**: `https://your-api.up.railway.app`
- **API Docs**: `https://your-api.up.railway.app/docs`
- **Frontend App**: `https://your-frontend.up.railway.app`

Share these URLs to let others use your app!

---

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Streamlit Cloud](https://streamlit.io/cloud) (Alternative for frontend)

---

**Need Help?** Check Railway's [Discord](https://discord.gg/railway) or [Documentation](https://docs.railway.app)

