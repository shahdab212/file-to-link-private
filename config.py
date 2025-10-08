"""
Configuration module for Telegram File-to-Link Bot
Handles environment variables and application settings
"""

import os
from typing import Optional

class Config:
    """Configuration class for the Telegram bot and web server"""
    
    # Telegram Bot Configuration
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Web Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    BASE_URL: str = os.getenv("BASE_URL", f"http://localhost:{PORT}")
    
    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # File Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "4294967296"))  # 4GB in bytes
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1048576"))  # 1MB chunks

    # Streaming Optimization Configuration
    INITIAL_CHUNK_SIZE: int = int(os.getenv("INITIAL_CHUNK_SIZE", "65536"))  # 64KB initial chunks for fast startup
    MAX_CHUNK_SIZE: int = int(os.getenv("MAX_CHUNK_SIZE", "1048576"))  # 1MB max chunks
    BUFFER_SIZE_MULTIPLIER: int = int(os.getenv("BUFFER_SIZE_MULTIPLIER", "4"))  # Scale up chunk size after initial buffer
    STREAM_TIMEOUT: int = int(os.getenv("STREAM_TIMEOUT", "30"))  # Stream timeout in seconds
    PRELOAD_ENABLED: bool = os.getenv("PRELOAD_ENABLED", "true").lower() == "true"
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Session Configuration
    SESSION_NAME: str = os.getenv("SESSION_NAME", "file_bot_session")
    
    # Channel and Media Group Configuration
    TELEGRAM_CHANNEL: str = os.getenv("TELEGRAM_CHANNEL", "")  # Channel username or invite link
    MEDIA_GROUP_ID: str = os.getenv("MEDIA_GROUP_ID", "")  # Media group chat ID (negative number)
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_vars = ["API_ID", "API_HASH", "BOT_TOKEN"]
        missing_vars = []
        
        for var in required_vars:
            if not getattr(cls, var) or getattr(cls, var) == "0":
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        # Warn about optional but recommended variables
        optional_vars = ["TELEGRAM_CHANNEL", "MEDIA_GROUP_ID"]
        missing_optional = []
        
        for var in optional_vars:
            if not getattr(cls, var):
                missing_optional.append(var)
        
        if missing_optional:
            print(f"⚠️  Optional environment variables not set: {', '.join(missing_optional)}")
            print("   Some features may not work properly without these variables.")
        
        print("✅ Configuration validation passed")
        return True
    
    @classmethod
    def get_download_url(cls, file_id: str, filename: str = None) -> str:
        """Generate download URL for a file"""
        if filename:
            # URL encode the filename and add it as a path parameter
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            return f"{cls.BASE_URL}/download/{file_id}/{safe_filename}"
        return f"{cls.BASE_URL}/download/{file_id}"
    
    @classmethod
    def get_stream_url(cls, file_id: str, filename: str = None) -> str:
        """Generate streaming URL for a file"""
        if filename:
            # URL encode the filename and add it as a path parameter
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            return f"{cls.BASE_URL}/stream/{file_id}/{safe_filename}"
        return f"{cls.BASE_URL}/stream/{file_id}"
    
    @classmethod
    def get_player_url(cls, file_id: str, filename: str = None) -> str:
        """Generate player URL for a file"""
        if filename:
            # URL encode the filename and add it as a path parameter
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            return f"{cls.BASE_URL}/play/{file_id}/{safe_filename}"
        return f"{cls.BASE_URL}/play/{file_id}"
    
    @classmethod
    def get_vlc_android_url(cls, file_id: str, filename: str = None) -> str:
        """Generate VLC Android intent URL for a file"""
        if filename:
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            stream_url = f"{cls.BASE_URL}/stream/{file_id}/{safe_filename}"
        else:
            stream_url = f"{cls.BASE_URL}/stream/{file_id}"
        
        return f"intent:{stream_url}#Intent;package=org.videolan.vlc;type=video/*;category=android.intent.category.DEFAULT;scheme=http;end"
    
    @classmethod
    def get_vlc_desktop_url(cls, file_id: str, filename: str = None) -> str:
        """Generate VLC desktop URL for a file"""
        if filename:
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            stream_url = f"{cls.BASE_URL}/stream/{file_id}/{safe_filename}"
        else:
            stream_url = f"{cls.BASE_URL}/stream/{file_id}"
        
        return f"vlc://{stream_url}"
