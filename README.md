# 🤖 Telegram File-to-Link Bot

A high-performance Telegram bot that generates direct download and streaming links for files shared on Telegram. Built with Python, Pyrogram, and AIOHTTP for maximum efficiency and scalability.

## ✨ Features

- 🚀 **High Performance**: Built with Pyrogram and AIOHTTP for optimal speed
- 📁 **Large File Support**: Handles files up to 4GB
- 🎬 **Smart Streaming**: Direct streaming without downloading to server disk
- 📱 **Mobile Friendly**: Responsive web player with modern UI
- 🔒 **Secure**: Environment-based configuration and secure file handling
- ⚡ **Fast Response**: Instant link generation with caching
- 🎯 **Range Requests**: Supports HTTP range requests for video streaming
- 📊 **Production Ready**: Comprehensive logging and error handling
- 🔐 **Channel Protection**: Requires users to join specified channel
- 📤 **Media Group Forwarding**: Automatically forwards processed files to media group

## 🎯 Supported File Types

- 📹 **Videos**: MP4, MKV, AVI, MOV, and more
- 🎵 **Audio**: MP3, FLAC, WAV, AAC, and more  
- 📄 **Documents**: PDF, ZIP, APK, EXE, and more

## 🚀 Quick Start

### Prerequisites

1. **Telegram API Credentials**:
   - Visit [my.telegram.org/apps](https://my.telegram.org/apps)
   - Create a new application
   - Note down your `API_ID` and `API_HASH`

2. **Bot Token**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot with `/newbot`
   - Save the bot token

### Local Development

1. **Clone and Setup**:
   ```bash
   git clone <your-repo-url>
   cd telegram-file-bot
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run the Bot**:
   ```bash
   python bot_main.py
   ```

## 🐳 Docker Deployment

1. **Build Docker Image**:
   ```bash
   docker build -t telegram-file-bot .
   ```

2. **Run Container**:
   ```bash
   docker run -d \
     --name telegram-file-bot \
     -p 8080:8080 \
     --env-file .env \
     telegram-file-bot
   ```

## 🚀 Heroku Deployment

1. **Install Heroku CLI** and login to your account

2. **Create Heroku App**:
   ```bash
   heroku create your-app-name
   ```

3. **Set Environment Variables**:
   ```bash
   heroku config:set API_ID=your_api_id
   heroku config:set API_HASH=your_api_hash
   heroku config:set BOT_TOKEN=your_bot_token
   heroku config:set BASE_URL=https://your-app-name.herokuapp.com
   # Add other environment variables as needed
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

## 📱 How to Use

1. **Start the Bot**:
   - Send `/start` to your bot on Telegram
   - Join the required channel if prompted
   - Read the welcome message

2. **Generate Links**:
   - Send any video, audio, or document file to the bot
   - Reply to that file message with `/dl`, `/dlink`, `.dl`, or `.dlink`
   - Get instant download and streaming links!

3. **Use the Links**:
   - Click "📥 Download" for direct file download
   - Click "📺 Stream" for web player streaming
   - Links work on all devices and browsers

## 🏗️ Project Structure

```
telegram-file-bot/
├── bot_main.py          # Main bot logic and command handlers
├── web_server.py        # AIOHTTP web server for file serving
├── config.py           # Configuration and environment management
├── utils/
│   └── media_utils.py  # Media processing utilities
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── Dockerfile         # Docker configuration
├── Procfile          # Heroku deployment configuration
└── README.md         # This file
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_ID` | Required | Telegram API ID |
| `API_HASH` | Required | Telegram API Hash |
| `BOT_TOKEN` | Required | Bot token from BotFather |
| `BASE_URL` | `http://localhost:8080` | Base URL for file links |
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8080` | Server port number |
| `SECRET_KEY` | `your-secret-key-here` | Security secret key |
| `MAX_FILE_SIZE` | `4294967296` | Max file size (4GB) |
| `CHUNK_SIZE` | `1048576` | Streaming chunk size (1MB) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SESSION_NAME` | `file_bot_session` | Pyrogram session name |
| `TELEGRAM_CHANNEL` | Optional | Channel users must join |
| `MEDIA_GROUP_ID` | Optional | Media group for file forwarding |

### File Size Limits

- **Maximum file size**: 4GB (configurable)
- **Streaming chunk size**: 1MB (configurable)
- **Supported by Telegram**: Up to 2GB via Bot API, 4GB via MTProto

## 🛠️ Advanced Features

### Web Player
- Modern HTML5 video/audio player with glassmorphism UI
- Keyboard shortcuts (Space, Arrow keys) for media control
- Copy-to-clipboard functionality with visual feedback
- Mobile-responsive design for all screen sizes
- Automatic file type detection and appropriate player selection

### Channel Protection
- Requires users to join specified channel before using the bot
- Supports both channel usernames and invite links
- Automatic membership verification on each command

### Media Group Forwarding
- Automatically forwards processed files to specified media group
- Includes detailed file information and user details
- Provides generated links for monitoring purposes

### HTTP Range Requests
The bot supports HTTP range requests, enabling:
- Video seeking in browsers
- Partial content delivery
- Bandwidth optimization
- Better mobile experience

### Error Handling
- Comprehensive error logging
- User-friendly error messages
- Automatic retry mechanisms
- Graceful degradation

## 🔍 Monitoring and Health Checks

### Health Check Endpoint
- Endpoint: `GET /health`
- Returns: `{"status": "healthy", "service": "telegram-file-bot"}`

### Available Commands
- `/start` - Start the bot and show welcome message
- `/help` - Show detailed help information
- `/dl`, `/dlink`, `.dl`, `.dlink` - Generate download links (reply to file)

## 🚨 Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check environment variables are set correctly
   - Verify bot token is valid
   - Check application logs

2. **Links not working**:
   - Verify `BASE_URL` is set correctly
   - Check if web server is running on correct port
   - Ensure firewall allows traffic on specified port

3. **File not found errors**:
   - Original message may be deleted
   - File may have expired on Telegram
   - Check file permissions and access

4. **Channel membership issues**:
   - Verify `TELEGRAM_CHANNEL` is set correctly
   - Check channel username format (@channel or https://t.me/channel)
   - Ensure bot has access to check membership

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python bot_main.py
```

## 🔒 Security Considerations

1. **Environment Variables**: Never commit sensitive data to version control
2. **Secret Key**: Use a strong, unique secret key for production
3. **File Access**: Links are temporary and secure
4. **Rate Limiting**: Built-in Telegram rate limiting protection
5. **HTTPS**: Always use HTTPS in production environments
6. **Channel Protection**: Restrict bot access to channel members only

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- **Issues**: Create a GitHub issue
- **Questions**: Check existing issues first
- **Updates**: Watch the repository for updates

## 🎉 Acknowledgments

- [Pyrogram](https://github.com/pyrogram/pyrogram) - Modern Telegram MTProto API framework
- [AIOHTTP](https://github.com/aio-libs/aiohttp) - Asynchronous HTTP client/server framework

---

**Made with ❤️ for the Telegram community**

*Happy file sharing! 🚀*
