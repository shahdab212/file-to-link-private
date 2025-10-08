# 🚀 Complete Render Deployment Guide

This guide provides step-by-step instructions for deploying your Telegram File-to-Link Bot on Render.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Telegram API Credentials** (API_ID and API_HASH from [my.telegram.org](https://my.telegram.org/apps))
- [ ] **Bot Token** (from [@BotFather](https://t.me/BotFather))
- [ ] **GitHub Account** (for code repository)
- [ ] **Render Account** (free at [render.com](https://render.com))

## 🔧 Step 1: Get Telegram Credentials

### Get API Credentials
1. Visit [my.telegram.org/apps](https://my.telegram.org/apps)
2. Log in with your phone number
3. Click "Create application"
4. Fill in the form:
   - **App title**: `File Link Bot`
   - **Short name**: `filelinkbot`
   - **Platform**: Choose any
5. Save your `API_ID` and `API_HASH`

### Get Bot Token
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a name: `My File Link Bot`
4. Choose a username: `myfilelinkbot` (must end with 'bot')
5. Save the bot token (format: `1234567890:ABCdef...`)

## 📁 Step 2: Prepare Your Repository

### Option A: Fork This Repository
1. Fork this repository on GitHub
2. Clone your fork locally
3. Make any customizations needed

### Option B: Create New Repository
1. Create a new repository on GitHub
2. Upload all the bot files to your repository
3. Ensure all files are committed and pushed

## 🌐 Step 3: Deploy on Render

### Create Web Service
1. Go to [render.com](https://render.com) and sign up/login
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if not already connected
4. Select your repository containing the bot code

### Configure Service Settings

#### Basic Settings
```
Name: telegram-file-bot
Environment: Python 3
Region: Choose closest to your users
Branch: main (or your default branch)
```

#### Build & Deploy Settings
```
Build Command: pip install -r requirements.txt
Start Command: python bot_main.py
```

#### Advanced Settings
```
Python Version: 3.11.0
Health Check Path: /health
Auto-Deploy: Yes
```

## 🔐 Step 4: Configure Environment Variables

In your Render service dashboard, go to **Environment** tab and add these variables:

### Required Variables
```bash
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
BASE_URL=https://your-service-name.onrender.com
SECRET_KEY=generate-a-random-secret-key
```

### Optional Variables (with defaults)
```bash
HOST=0.0.0.0
PORT=10000
LOG_LEVEL=INFO
MAX_FILE_SIZE=4294967296
CHUNK_SIZE=1048576
SESSION_NAME=file_bot_session
```

### How to Set Environment Variables
1. In your Render service dashboard
2. Go to **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Enter **Key** and **Value**
5. Click **"Save Changes"**

## 🚀 Step 5: Deploy and Test

### Deploy the Service
1. Click **"Create Web Service"** or **"Manual Deploy"**
2. Wait for the build to complete (usually 2-5 minutes)
3. Check the **"Logs"** tab for any errors

### Verify Deployment
1. Visit your service URL: `https://your-service-name.onrender.com/health`
2. Should return: `{"status": "healthy", "service": "telegram-file-bot"}`
3. Check logs for "Bot started successfully" message

### Test the Bot
1. Find your bot on Telegram (search for your bot username)
2. Send `/start` to the bot
3. Upload a test file (video, audio, or document)
4. Reply to the file with `/fdl`
5. Verify that download and stream links work

## 🔍 Step 6: Monitoring and Maintenance

### Check Service Health
- **Service URL**: `https://your-service-name.onrender.com`
- **Health Check**: `https://your-service-name.onrender.com/health`
- **Logs**: Available in Render dashboard

### Monitor Performance
1. Go to your Render service dashboard
2. Check **"Metrics"** tab for:
   - Response times
   - Memory usage
   - CPU usage
   - Request volume

### Update the Bot
1. Push changes to your GitHub repository
2. Render will automatically redeploy (if auto-deploy is enabled)
3. Or manually trigger deployment in Render dashboard

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### 1. Bot Not Starting
**Symptoms**: Service fails to start, error in logs
**Solutions**:
- Check all environment variables are set correctly
- Verify API_ID, API_HASH, and BOT_TOKEN are valid
- Check Python syntax errors in logs

#### 2. Links Not Working
**Symptoms**: Bot responds but links don't work
**Solutions**:
- Verify BASE_URL matches your Render service URL
- Check if web server is running (health check should work)
- Ensure PORT is set to 10000

#### 3. File Not Found Errors
**Symptoms**: "File not found" when accessing links
**Solutions**:
- Original Telegram message may be deleted
- File may have expired
- Check bot has access to the chat/channel

#### 4. Memory Issues
**Symptoms**: Service crashes, out of memory errors
**Solutions**:
- Reduce CHUNK_SIZE (try 512KB: `524288`)
- Reduce MAX_FILE_SIZE if needed
- Upgrade to a higher Render plan

### Debug Mode
To enable detailed logging:
1. Set environment variable: `LOG_LEVEL=DEBUG`
2. Redeploy the service
3. Check logs for detailed information

### Service Logs
Access logs in Render dashboard:
1. Go to your service
2. Click **"Logs"** tab
3. Use filters to find specific issues

## 📊 Performance Optimization

### For Better Performance
1. **Choose the right region**: Deploy close to your users
2. **Optimize chunk size**: Balance between memory and speed
3. **Monitor metrics**: Keep an eye on response times
4. **Upgrade plan**: If you have high traffic

### Recommended Settings for High Traffic
```bash
CHUNK_SIZE=2097152  # 2MB chunks
LOG_LEVEL=WARNING   # Reduce log verbosity
```

## 💰 Render Pricing

### Free Tier Limitations
- 750 hours/month (enough for 24/7 operation)
- Service sleeps after 15 minutes of inactivity
- 512MB RAM, 0.1 CPU

### Paid Plans
- **Starter ($7/month)**: No sleep, 512MB RAM
- **Standard ($25/month)**: 2GB RAM, better performance
- **Pro ($85/month)**: 4GB RAM, high performance

## 🔒 Security Best Practices

1. **Never commit secrets**: Use environment variables only
2. **Use strong secret key**: Generate a random 32+ character key
3. **Monitor access**: Check logs regularly
4. **Keep dependencies updated**: Update requirements.txt regularly
5. **Use HTTPS**: Always use your Render HTTPS URL

## 📞 Getting Help

### If You Need Support
1. **Check logs first**: Most issues are visible in logs
2. **Verify configuration**: Double-check all environment variables
3. **Test locally**: Try running the bot locally first
4. **GitHub Issues**: Create an issue with logs and configuration

### Useful Resources
- [Render Documentation](https://render.com/docs)
- [Pyrogram Documentation](https://docs.pyrogram.org)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## ✅ Deployment Checklist

Before going live, verify:

- [ ] All environment variables are set correctly
- [ ] Health check endpoint returns success
- [ ] Bot responds to `/start` command
- [ ] File upload and `/fdl` command works
- [ ] Download links work in browser
- [ ] Stream links work for videos
- [ ] Logs show no errors
- [ ] Service doesn't sleep (if on paid plan)

## 🎉 Success!

If everything is working:
- Your bot is live at `@your_bot_username`
- Web service is running at `https://your-service-name.onrender.com`
- Users can generate file links by replying with `/fdl`

**Congratulations! Your Telegram File-to-Link Bot is now live! 🚀**

---

*Need help? Create an issue on GitHub with your logs and configuration details.*
