# 🚀 E-Commerce Deployment Guide

## Quick Start - Choose Your Platform

### Option 1: Render (Recommended - Free Tier Available)
✅ Free MySQL database included
✅ Free Redis included
✅ Easy SSL setup
✅ GitHub integration

### Option 2: Railway (Best Developer Experience)
✅ Excellent UI
✅ Easy database provisioning
✅ $5 free credit monthly
✅ GitHub integration

### Option 3: Fly.io (Advanced)
✅ Global edge deployment
✅ Free allowance
⚠️ Requires Docker knowledge

---

## 📋 Pre-Deployment Checklist

### 1. Environment Variables You MUST Set

**Production Security:**
```bash
FLASK_ENV=production
PRODUCTION=True
SECRET_KEY=<generate-random-64-char-string>
```

**Database (MySQL):**
```bash
MYSQL_HOST=<your-db-host>
MYSQL_USER=<your-db-user>
MYSQL_PASSWORD=<your-db-password>
MYSQL_DB=ecommerce
MYSQL_PORT=3306
```

**Redis (Sessions/Cache):**
```bash
REDIS_HOST=<your-redis-host>
REDIS_PORT=6379
REDIS_PASSWORD=<your-redis-password>
REDIS_DB=0
```

**MTN MoMo Payment:**
```bash
MOMO_COLLECTIONS_SUBKEY=<your-momo-key>
MOMO_ENV_MODE=sandbox  # Change to 'production' when ready
MOMO_API_USER=<optional-if-exists>
MOMO_API_KEY=<optional-if-exists>
```

**Google OAuth (Optional):**
```bash
GOOGLE_CLIENT_ID=<your-client-id>.googleusercontent.com
GOOGLE_REDIRECT_URI=https://your-domain.com/google/callback
```

**Email (Optional):**
```bash
GMAIL_USER=<your-email@gmail.com>
GMAIL_APP_PASSWORD=<your-app-password>
```

---

## 🎯 Step-by-Step: Deploy to Render

### Step 1: Prepare Your Code
```bash
# Make sure all files are committed
git init  # if not already a git repo
git add .
git commit -m "Ready for deployment"

# Push to GitHub
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

### Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub
3. Authorize Render to access your repos

### Step 3: Create MySQL Database
1. Dashboard → New → MySQL
2. Name: `ecommerce-db`
3. Database: `ecommerce`
4. User: `ecommerce_user`
5. Region: Choose closest to your users
6. Instance Type: **Free** (or paid for production)
7. Click **Create Database**
8. **Save the connection details** (Internal/External URLs)

### Step 4: Create Redis Instance
1. Dashboard → New → Redis
2. Name: `ecommerce-redis`
3. Region: Same as database
4. Instance Type: **Free**
5. Click **Create Redis**
6. **Save the connection URL**

### Step 5: Import Your Database
1. Connect to your Render MySQL instance using a MySQL client
2. Import your local database:
   ```bash
   # Export from local XAMPP
   mysqldump -u root -p ecommerce > ecommerce_backup.sql
   
   # Import to Render (use connection details from Step 3)
   mysql -h <render-host> -u <user> -p<password> ecommerce < ecommerce_backup.sql
   ```

### Step 6: Deploy Web Service
1. Dashboard → New → Web Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `your-ecommerce-site`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: Leave blank (uses Procfile)
   - **Instance Type**: Free (or paid)

### Step 7: Set Environment Variables
In Render dashboard → Environment:

```bash
# Production Mode
FLASK_ENV=production
PRODUCTION=True
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">

# Database (from Step 3)
MYSQL_HOST=<from-render-internal-url>
MYSQL_USER=ecommerce_user
MYSQL_PASSWORD=<from-render>
MYSQL_DB=ecommerce
MYSQL_PORT=3306

# Redis (from Step 4)
REDIS_HOST=<from-render-internal-url>
REDIS_PORT=6379
REDIS_PASSWORD=<from-render>
REDIS_DB=0

# MTN MoMo
MOMO_COLLECTIONS_SUBKEY=<your-key>
MOMO_ENV_MODE=sandbox
# Add MOMO_API_USER and MOMO_API_KEY if you have them

# Google OAuth (update after deployment)
GOOGLE_CLIENT_ID=<your-id>
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/google/callback

# Email
GMAIL_USER=<your-email>
GMAIL_APP_PASSWORD=<your-app-password>
```

### Step 8: Deploy!
1. Click **Create Web Service**
2. Wait 5-10 minutes for build
3. Your site will be live at: `https://your-app.onrender.com`

### Step 9: Update Google OAuth
1. Go to Google Cloud Console
2. Update Authorized Redirect URIs:
   - Add: `https://your-app.onrender.com/google/callback`
3. Update Authorized JavaScript Origins:
   - Add: `https://your-app.onrender.com`

---

## 🚂 Alternative: Deploy to Railway

### Quick Railway Setup
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway init

# Add MySQL
railway add --plugin mysql

# Add Redis
railway add --plugin redis

# Set environment variables
railway variables set FLASK_ENV=production
railway variables set PRODUCTION=True
railway variables set SECRET_KEY=<your-secret-key>
# ... add all other variables

# Deploy
railway up

# Get your URL
railway domain
```

---

## 🔒 Production Security Checklist

- [ ] Generate strong SECRET_KEY (64+ characters)
- [ ] Set PRODUCTION=True
- [ ] Use HTTPS only (automatic on Render/Railway)
- [ ] Enable firewall rules on database
- [ ] Whitelist only your app's IP for database access
- [ ] Use environment variables (never hardcode secrets)
- [ ] Set up automated backups for database
- [ ] Enable Redis password authentication
- [ ] Review CSP headers in app.py
- [ ] Test all payment flows in sandbox first
- [ ] Set up monitoring/alerts

---

## 🐛 Troubleshooting

### Database Connection Fails
```python
# Check if MySQL port is correct (usually 3306)
# Ensure you're using INTERNAL database URL (faster, more secure)
# Verify database user has proper permissions
```

### Redis Connection Fails
```python
# Check REDIS_PASSWORD is set correctly
# Verify Redis is in same region as web service
# Use internal Redis URL for better performance
```

### Static Files Not Loading
```python
# Render/Railway automatically serve /static folder
# Verify static files are committed to git
# Check file paths are relative: /static/...
```

### Payment Integration Issues
```python
# Start with MOMO_ENV_MODE=sandbox
# Use test phone numbers: 46733123450
# Check MTN MoMo credentials are correct
# Review logs for API error responses
```

---

## 📊 Post-Deployment

### Monitor Your App
- Check Render/Railway logs regularly
- Set up uptime monitoring (UptimeRobot, etc.)
- Monitor database usage
- Track Redis memory usage

### Performance Optimization
- Enable caching (already implemented with Redis)
- Use CDN for static files (Cloudflare)
- Optimize database queries
- Enable GZIP compression (already enabled)

### Scaling
- Upgrade instance type for more traffic
- Add more workers in Procfile
- Consider read replicas for database
- Use managed CDN for images

---

## 🎉 You're Live!

Your e-commerce site should now be live and secure. Test thoroughly before announcing:

1. ✅ Homepage loads
2. ✅ Product pages work
3. ✅ Cart functionality
4. ✅ Checkout flow
5. ✅ MTN MoMo payments (sandbox)
6. ✅ Email notifications
7. ✅ Google OAuth login
8. ✅ Admin panel access
9. ✅ Mobile responsive
10. ✅ HTTPS enabled

---

## 💡 Need Help?

- Render Docs: https://render.com/docs
- Railway Docs: https://docs.railway.app
- MTN MoMo: https://momodeveloper.mtn.com
- Your app logs: Check dashboard → Logs

**Remember:** Start with sandbox/test mode for payments, then switch to production after thorough testing!
