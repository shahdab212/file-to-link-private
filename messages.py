class Messages:
    """Centralized messages for the bot"""
    
    WELCOME = (
        "🤖 **Welcome to File-to-Link Bot!**\n\n"
        "📁 I can generate direct download and streaming links for your Telegram files.\n\n"
    )
    
    JOIN_CHANNEL = (
        "💡 **Stay Updated!**\n"
        "Join our update channel to get notified about new features and updates!\n\n"
    )
    
    USAGE_INSTRUCTIONS = (
        "**How to use:**\n"
        "1. Forward or send any video, audio, or document file\n"
        "2. Reply to that message with `/dl`, `/dlink`, `.dl`, or `.dlink`\n"
        "3. Get instant download and streaming links!\n\n"
        "**Supported files:**\n"
        "• 📹 Videos (up to 4GB)\n"
        "• 🎵 Audio files\n"
        "• 📄 Documents\n\n"
        "**Features:**\n"
        "• ⚡ Fast streaming without downloading\n"
        "• 📱 Mobile-friendly links\n"
        "• 🔒 Secure file handling\n\n"
        "Try it now by sending a file and replying with any download command!"
    )
    
    HELP_TEXT = (
        "📖 **Help - How to Use File-to-Link Bot**\n\n"
        "**Step-by-step guide:**\n\n"
        "1️⃣ **Send a file**: Upload any video, audio, or document to the chat\n"
        "2️⃣ **Reply with a download command**: Reply to the file message with `/dl`, `/dlink`, `.dl`, or `.dlink`\n"
        "3️⃣ **Get your links**: Receive download and streaming links instantly!\n\n"
        "**Available commands:**\n"
        "• `/dl` - Generate download links\n"
        "• `/dlink` - Generate download links\n"
        "• `.dl` - Generate download links\n"
        "• `.dlink` - Generate download links\n\n"
        "**Supported file types:**\n"
        "• 🎬 Video files (.mp4, .mkv, .avi, etc.)\n"
        "• 🎵 Audio files (.mp3, .flac, .wav, etc.)\n"
        "• 📄 Document files (.pdf, .zip, .apk, etc.)\n\n"
        "**File size limit:** Up to 4GB per file\n\n"
        "**Example usage:**\n"
        "```\n"
        "User: [sends video.mp4]\n"
        "User: /dl (as reply to the video)\n"
        "Bot: [generates links with buttons]\n"
        "```\n\n"
        "**Need more help?** Contact support or check our documentation."
    )
    
    ABOUT_TEXT = (
        "ℹ️ **About File-to-Link Bot**\n\n"
        "🚀 High-performance Telegram file linking service\n"
        "⚡ Built with Pyrogram + AIOHTTP\n"
        "🔒 Secure and efficient file streaming\n"
        "📱 Mobile-friendly interface\n\n"
        "Version: 1.0.0"
    )
    
    QUICK_HELP = (
        "📖 **Quick Help**\n\n"
        "1. Send or forward a file\n"
        "2. Reply to it with `/dl`\n"
        "3. Get download links!\n\n"
        "Supported: Videos, Audio, Documents"
    )
    
    ERR_NO_REPLY = (
        "❌ **Please reply to a file message with a download command**\n\n"
        "📝 **How to use:**\n"
        "1. Find a message with a video, audio, or document\n"
        "2. Reply to that message with `/dl`, `/dlink`, `.dl`, or `.dlink`\n"
        "3. Get your download links!\n\n"
        "💡 **Tip:** You can forward files from other chats and then use any download command"
    )
    
    ERR_NO_FILE = (
        "❌ **No supported file found!**\n\n"
        "📁 **Supported file types:**\n"
        "• 📹 Videos\n"
        "• 🎵 Audio files\n"
        "• 📄 Documents\n\n"
        "Please reply to a message containing one of these file types."
    )
    
    ERR_FILE_TOO_LARGE = (
        "❌ **File too large!**\n\n"
        "📏 **File size:** {size}\n"
        "📏 **Maximum allowed:** {max_size}\n\n"
        "Please try with a smaller file."
    )
    
    ERR_GENERIC = (
        "❌ **An error occurred while processing your request.**\n\n"
        "Please try again in a few moments. If the problem persists, "
        "contact support with the error details."
    )
    
    ERR_CALLBACK = "❌ An error occurred. Please try again."
    
    RESPONSE_TEMPLATE_HEADER = (
        "📝 **File Name:** {name}\n"
        "📏 **File Size:** {size}\n"
        "🗂️ **File Type:** {type}\n"
        "🔗 **MIME Type:** {mime}\n"
    )
    
    RESPONSE_STREAMABLE = (
        "🎵 **Streamable:** Yes\n\n"
        "📥 **Download:** `{download_url}`\n\n"
        "🎵 **Stream:** `{stream_url}`\n\n"
        "💡 **Tip:** Use the Web Stream button for web player or copy the Stream URL for VLC"
    )
    
    RESPONSE_DOWNLOAD_ONLY = "\n📥 **Download:** `{download_url}`"
