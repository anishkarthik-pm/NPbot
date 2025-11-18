# Deployment Guide

## Important: Vercel is NOT Supported

This application **cannot be deployed on Vercel** because it requires:
- Persistent storage for ChromaDB vector database and scraped data
- Support for large ML packages (pandas, chromadb) exceeding 250 MB
- Long-running background jobs for web scraping
- Stateful data directory

## Recommended Platforms

### Option 1: Railway (Recommended) ⭐

Railway is the easiest and most suitable platform for this application.

**Steps:**

1. **Create Railway Account**: Go to [railway.app](https://railway.app) and sign up

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure Environment Variables**:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   PORT=8000
   ```

4. **Add Persistent Volume** (Important!):
   - Go to your service settings
   - Click "Variables" → "Volumes"
   - Add volume: `/app/data` (this will persist your scraped data)

5. **Deploy**: Railway will automatically detect the `Procfile` and deploy

**Free Tier**: Railway offers $5/month free credit, sufficient for development.

---

### Option 2: Render

**Steps:**

1. **Create Render Account**: Go to [render.com](https://render.com)

2. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

3. **Configure**:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `sh -c 'uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}'`
   - **Python Version**: 3.11.9

4. **Add Disk**:
   - Go to "Disks" section
   - Add disk mounted at `/app/data`
   - Size: 1 GB minimum

5. **Environment Variables**:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   PYTHON_VERSION=3.11.9
   ```

**Free Tier**: Render offers a free tier with limitations (spins down after inactivity).

---

### Option 3: Docker (Any Container Platform)

You can deploy using the included `Dockerfile` to:
- **Google Cloud Run**
- **AWS ECS/Fargate**
- **Azure Container Instances**
- **Fly.io**
- **DigitalOcean App Platform**

**Build and Run Locally**:
```bash
# Build
docker build -t npbot .

# Run
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  npbot
```

**Deploy to Cloud**:
1. Push to container registry (Docker Hub, GCR, ECR, etc.)
2. Deploy to your chosen platform
3. **Important**: Configure persistent volume at `/app/data`

---

## Environment Variables

Required environment variables for all platforms:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | Yes |
| `PORT` | Port to run the server (default: 8000) | No |
| `VALIDATION_ENABLED` | Enable data validation (default: True) | No |

---

## Post-Deployment

### 1. Initial Data Scraping

After deployment, you need to scrape the initial data:

```bash
# SSH into your deployment or use platform terminal
python main.py --scrape
```

This will populate the `data/` directory with mutual fund information.

### 2. Test the API

```bash
# Health check
curl https://your-app-url/health

# Test query
curl -X POST https://your-app-url/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the NAV of Nippon India Small Cap Fund?"}'
```

### 3. Setup Scheduler (Optional)

For periodic data updates, run:
```bash
python main.py --scheduler
```

Or set up a cron job / scheduled task on your platform.

---

## Persistent Storage Requirements

The application needs persistent storage for:

- `/app/data/schemes/` - Scraped scheme data (JSON)
- `/app/data/factsheets/` - Factsheet data (JSON)
- `/app/data/chunks/` - Text chunks for RAG
- `/app/data/chromadb/` - Vector database (if using local ChromaDB)

**Minimum disk space**: 1 GB
**Recommended**: 5 GB for growth

---

## Troubleshooting

### Build Fails with "Package too large"
- You're likely trying to deploy on Vercel. Use Railway or Render instead.

### "ChromaDB not initialized"
- Make sure persistent storage is mounted at `/app/data`
- Run the initial scraping: `python main.py --scrape`

### "OPENROUTER_API_KEY not set"
- Add the environment variable in your platform's settings

### "Module not found" errors
- Ensure Python 3.11+ is being used
- All dependencies in requirements.txt are compatible with Python 3.11+

---

## Cost Estimates

| Platform | Free Tier | Paid (Starter) |
|----------|-----------|----------------|
| Railway | $5/month credit | ~$5-10/month |
| Render | 750 hours/month | $7/month |
| Fly.io | 3 shared CPUs | ~$5/month |
| DigitalOcean | $200 credit (60 days) | $5/month |

For development/testing, Railway or Render's free tiers are sufficient.

---

## Need Help?

If you encounter issues:
1. Check the platform logs
2. Verify environment variables are set
3. Ensure persistent storage is configured
4. Confirm Python 3.11+ is being used

For platform-specific help:
- Railway: [docs.railway.app](https://docs.railway.app)
- Render: [render.com/docs](https://render.com/docs)
