# Deployment Guide

This guide explains how to deploy CrimeVision AI to production using Render (backend) and Vercel (frontend).

## Prerequisites

- GitHub account with the repository pushed
- Render account (free tier available)
- Vercel account (free tier available)
- Groq API key (for AI features)

## Backend Deployment (Render)

### Step 1: Create Render Account

1. Go to [render.com](https://render.com) and sign up
2. Connect your GitHub account

### Step 2: Deploy Backend

1. In Render dashboard, click "New +"
2. Select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: crimevision-backend
   - **Region**: Choose closest to your users
   - **Branch**: main
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c .gunicorn.conf.py run:app`

5. Add Environment Variables:
   - `FLASK_ENV`: `production`
   - `PORT`: `10000`
   - `DATABASE_URL`: `sqlite:///crimevision.db`
   - `SECRET_KEY`: (generate a random string)
   - `GROQ_API_KEY`: Your Groq API key
   - `GROQ_MODEL`: `gemma2-9b-it` (or your preferred model)
   - `CORS_ORIGINS`: Your Vercel frontend URL (e.g., `https://your-app.vercel.app`)

6. Click "Create Web Service"

### Step 3: Note the Backend URL

After deployment, Render will provide a URL like:
```
https://crimevision-backend.onrender.com
```

Save this URL for the frontend configuration.

## Frontend Deployment (Vercel)

### Step 1: Create Vercel Account

1. Go to [vercel.com](https://vercel.com) and sign up
2. Connect your GitHub account

### Step 2: Deploy Frontend

1. In Vercel dashboard, click "Add New Project"
2. Import your GitHub repository
3. Configure the project:
   - **Framework Preset**: Vite
   - **Root Directory**: frontend
   - **Build Command**: `npm run build`
   - **Output Directory**: dist

4. Add Environment Variables:
   - `VITE_API_BASE_URL`: Your Render backend URL (e.g., `https://crimevision-backend.onrender.com`)

5. Click "Deploy"

### Step 3: Note the Frontend URL

After deployment, Vercel will provide a URL like:
```
https://your-app.vercel.app
```

## Post-Deployment Configuration

### Update CORS on Backend

1. Go to your Render dashboard
2. Open your backend service
3. Go to "Environment" section
4. Update `CORS_ORIGINS` to include your Vercel URL:
   ```
   https://your-app.vercel.app,https://crimevision-backend.onrender.com
   ```
5. Save and redeploy

### Verify Deployment

1. Visit your Vercel frontend URL
2. Check that the dashboard loads
3. Test uploading evidence
4. Test the chat feature (if Groq is configured)

## Free Tier Limitations

### Render Free Tier
- Spins down after 15 minutes of inactivity
- Cold start takes ~30 seconds
- 512 MB RAM
- Limited bandwidth

### Vercel Free Tier
- Always active
- 100 GB bandwidth/month
- Unlimited deployments
- Automatic SSL

## Troubleshooting

### Backend Issues

**Error: "Service Unavailable"**
- Check Render logs for errors
- Verify environment variables are set
- Ensure GROQ_API_KEY is valid

**CORS Errors**
- Verify CORS_ORIGINS includes your Vercel URL
- Check that the frontend URL is HTTPS

### Frontend Issues

**API Connection Errors**
- Verify VITE_API_BASE_URL is correct
- Check that backend is running on Render
- Ensure backend URL is accessible

**Build Failures**
- Check Vercel build logs
- Verify all dependencies are in package.json
- Ensure TypeScript compiles without errors

## Updating Deployments

### Backend Update
1. Push changes to GitHub
2. Render auto-deploys on push to main branch
3. Or manually trigger redeploy in Render dashboard

### Frontend Update
1. Push changes to GitHub
2. Vercel auto-deploys on push to main branch
3. Or manually trigger redeploy in Vercel dashboard

## Custom Domains (Optional)

### Frontend (Vercel)
1. Go to project settings in Vercel
2. Add custom domain
3. Update DNS records as instructed

### Backend (Render)
1. Go to service settings in Render
2. Add custom domain
3. Update DNS records as instructed
4. Update CORS_ORIGINS with new domain

## Security Notes

- Never commit `.env` files with real API keys
- Use Render's environment variables for secrets
- Enable HTTPS (both platforms provide this automatically)
- Consider rate limiting for production use
- Regularly update dependencies
