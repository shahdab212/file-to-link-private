"""
Main Telegram Bot Logic for File-to-Link Bot
Handles user interactions and command processing
"""

import asyncio
import logging
import hashlib
from typing import Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified
from config import Config
from web_server import start_web_server
from utils.media_utils import MediaProcessor

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileLinkBot:
    """Main bot class handling all Telegram interactions"""
    
    def __init__(self):
        self.bot = Client(
            Config.SESSION_NAME,
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.web_runner = None
        self.user_states = {}  # Track user states for channel verification
        
    def generate_file_id(self, message: Message) -> str:
        """Generate a unique file ID for the message"""
        return f"{message.chat.id}_{message.id}"
    
    def get_file_info(self, message: Message) -> Optional[dict]:
        """Extract file information from message"""
        if message.document:
            return {
                'type': 'document',
                'file': message.document,
                'name': message.document.file_name or f"document_{message.document.file_id[:8]}",
                'size': message.document.file_size,
                'mime_type': message.document.mime_type or 'application/octet-stream'
            }
        elif message.video:
            return {
                'type': 'video',
                'file': message.video,
                'name': message.video.file_name or f"video_{message.video.file_id[:8]}.mp4",
                'size': message.video.file_size,
                'mime_type': message.video.mime_type or 'video/mp4'
            }
        elif message.audio:
            return {
                'type': 'audio',
                'file': message.audio,
                'name': message.audio.file_name or f"audio_{message.audio.file_id[:8]}.mp3",
                'size': message.audio.file_size,
                'mime_type': message.audio.mime_type or 'audio/mpeg'
            }
        return None
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    async def check_channel_membership(self, user_id: int) -> bool:
        """Check if user is a member of the required channel"""
        if not Config.TELEGRAM_CHANNEL:
            return True  # No channel requirement set
        
        try:
            # Extract channel username from link if needed
            channel = Config.TELEGRAM_CHANNEL
            if channel.startswith('https://t.me/'):
                channel = channel.replace('https://t.me/', '@')
            elif not channel.startswith('@'):
                channel = f'@{channel}'
            
            # Check membership
            member = await self.bot.get_chat_member(channel, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            return True  # Allow access if check fails
    
    async def forward_to_media_group(self, message: Message, file_info: dict, enhanced_urls: dict):
        """Forward file information to media group"""
        if not Config.MEDIA_GROUP_ID:
            return  # No media group configured
        
        try:
            # Create media group message
            user_name = message.from_user.first_name
            if message.from_user.last_name:
                user_name += f" {message.from_user.last_name}"
            
            # Check if file is streamable for proper formatting
            is_streamable = MediaProcessor.is_streamable(file_info['name'], file_info.get('mime_type', ''))
            
            if is_streamable:
                links_text = (
                    f"🔗 **Links:**\n"
                    f"📥 Download: `{enhanced_urls['download_named']}`\n\n"
                    f"🎵 Stream: `{enhanced_urls['stream_named']}`"
                )
            else:
                links_text = (
                    f"🔗 **Links:**\n"
                    f"📥 Download: `{enhanced_urls['download_named']}`"
                )
            
            media_text = (
                f"📁 **New File Processed**\n\n"
                f"👤 **User:** [{user_name}](tg://user?id={message.from_user.id})\n"
                f"🆔 **User ID:** `{message.from_user.id}`\n"
                f"📝 **File Name:** {file_info['name']}\n"
                f"📏 **File Size:** {self.format_file_size(file_info['size'])}\n"
                f"🗂️ **File Type:** {file_info['type'].capitalize()}\n\n"
                f"{links_text}"
            )
            
            # Send the file directly without forwarding (removes forwarder sender name)
            replied_message = message.reply_to_message
            if replied_message.document:
                await self.bot.send_document(
                    Config.MEDIA_GROUP_ID,
                    replied_message.document.file_id,
                    caption=media_text,
                    disable_notification=True
                )
            elif replied_message.video:
                await self.bot.send_video(
                    Config.MEDIA_GROUP_ID,
                    replied_message.video.file_id,
                    caption=media_text,
                    disable_notification=True
                )
            elif replied_message.audio:
                await self.bot.send_audio(
                    Config.MEDIA_GROUP_ID,
                    replied_message.audio.file_id,
                    caption=media_text,
                    disable_notification=True
                )
            else:
                # Fallback: send just the text message if file type is not supported
                await self.bot.send_message(
                    Config.MEDIA_GROUP_ID,
                    media_text,
                    disable_web_page_preview=True
                )
            
            logger.info(f"Sent file to media group: {file_info['name']}")
            
        except Exception as e:
            logger.error(f"Error sending to media group: {e}")
    
    async def setup_handlers(self):
        """Setup all bot command and message handlers"""
        
        @self.bot.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            """Handle /start command"""
            user_id = message.from_user.id
            
            # Build welcome text
            welcome_text = (
                "🤖 **Welcome to File-to-Link Bot!**\n\n"
                "📁 I can generate direct download and streaming links for your Telegram files.\n\n"
            )
            
            # Add polite channel join suggestion if channel is configured
            if Config.TELEGRAM_CHANNEL:
                # Check if user is already a member (just for the personalized message)
                is_member = await self.check_channel_membership(user_id)
                if not is_member:
                    welcome_text += (
                        "💡 **Stay Updated!**\n"
                        "Join our update channel to get notified about new features and updates!\n\n"
                    )
            
            welcome_text += (
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
            
            # Create keyboard with help, about, and join channel buttons
            keyboard_buttons = [
                [InlineKeyboardButton("📖 Help", callback_data="help")],
                [InlineKeyboardButton("ℹ️ About", callback_data="about")]
            ]
            
            # Add join channel button if channel is configured
            if Config.TELEGRAM_CHANNEL:
                # Check if user is already a member to customize button text
                is_member = await self.check_channel_membership(user_id)
                if is_member:
                    keyboard_buttons.append([InlineKeyboardButton("✅ Update Channel", url=Config.TELEGRAM_CHANNEL)])
                else:
                    keyboard_buttons.append([InlineKeyboardButton("📢 Join Update Channel", url=Config.TELEGRAM_CHANNEL)])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            await message.reply_text(welcome_text, reply_markup=keyboard)
        
        @self.bot.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            """Handle /help command"""
            help_text = (
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
            
            await message.reply_text(help_text)
        
        @self.bot.on_message(filters.command(["dl", "dlink"]) | filters.regex(r"^\.dl$|^\.dlink$"))
        async def fdl_command(client: Client, message: Message):
            """Handle /dl, /dlink, .dl, and .dlink commands - main functionality"""
            try:
                # Check if this is a reply to a message
                if not message.reply_to_message:
                    await message.reply_text(
                        "❌ **Please reply to a file message with a download command**\n\n"
                        "📝 **How to use:**\n"
                        "1. Find a message with a video, audio, or document\n"
                        "2. Reply to that message with `/dl`, `/dlink`, `.dl`, or `.dlink`\n"
                        "3. Get your download links!\n\n"
                        "💡 **Tip:** You can forward files from other chats and then use any download command"
                    )
                    return
                
                replied_message = message.reply_to_message
                file_info = self.get_file_info(replied_message)
                
                if not file_info:
                    await message.reply_text(
                        "❌ **No supported file found!**\n\n"
                        "📁 **Supported file types:**\n"
                        "• 📹 Videos\n"
                        "• 🎵 Audio files\n"
                        "• 📄 Documents\n\n"
                        "Please reply to a message containing one of these file types."
                    )
                    return
                
                # Check file size
                if file_info['size'] > Config.MAX_FILE_SIZE:
                    max_size_formatted = self.format_file_size(Config.MAX_FILE_SIZE)
                    await message.reply_text(
                        f"❌ **File too large!**\n\n"
                        f"📏 **File size:** {self.format_file_size(file_info['size'])}\n"
                        f"📏 **Maximum allowed:** {max_size_formatted}\n\n"
                        "Please try with a smaller file."
                    )
                    return
                
                # Generate file ID and URLs
                file_id = self.generate_file_id(replied_message)
                
                # Generate URLs and get file info
                try:
                    # Generate URLs
                    enhanced_urls = MediaProcessor.generate_enhanced_urls(file_id, file_info['name'], Config.BASE_URL)
                    
                    # Get file type display name
                    file_type_display = MediaProcessor.get_file_type_display(file_info['name'], file_info['mime_type'])
                    
                    # Check if file is streamable
                    is_streamable = MediaProcessor.is_streamable(file_info['name'], file_info['mime_type'])
                    
                except Exception as media_error:
                    logger.error(f"Error processing media: {media_error}")
                    # Fallback to basic functionality
                    from urllib.parse import quote
                    safe_filename = quote(file_info['name'], safe='')
                    enhanced_urls = {
                        'download_named': f"{Config.BASE_URL}/download/{file_id}/{safe_filename}",
                        'stream_named': f"{Config.BASE_URL}/stream/{file_id}/{safe_filename}",
                        'play_named': f"{Config.BASE_URL}/play/{file_id}/{safe_filename}"
                    }
                    file_type_display = file_info['type'].capitalize()
                    is_streamable = file_info['type'] in ['video', 'audio']
                
                # Create response message with new format
                response_text = (
                    f"📝 **File Name:** {file_info['name']}\n"
                    f"📏 **File Size:** {self.format_file_size(file_info['size'])}\n"
                    f"🗂️ **File Type:** {file_type_display}\n"
                    f"🔗 **MIME Type:** {file_info['mime_type']}\n"
                )
                
                # Add streamable info and links only for streamable files
                if is_streamable:
                    response_text += f"🎵 **Streamable:** Yes\n\n"
                    response_text += f"📥 **Download:** `{enhanced_urls['download_named']}`\n\n"
                    response_text += f"🎵 **Stream:** `{enhanced_urls['stream_named']}`\n\n"
                    response_text += f"💡 **Tip:** Use the Web Stream button for web player or copy the Stream URL for VLC"
                else:
                    response_text += f"\n📥 **Download:** `{enhanced_urls['download_named']}`"
                
                # Create keyboard based on file type
                if is_streamable:
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📥 Download", url=enhanced_urls['download_named']),
                            InlineKeyboardButton("📺 Web Stream", url=enhanced_urls['play_named'])
                        ]
                    ])
                else:
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📥 Download", url=enhanced_urls['download_named'])
                        ]
                    ])
                
                await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
                
                # Forward to media group
                await self.forward_to_media_group(message, file_info, enhanced_urls)
                
                # Log successful link generation
                logger.info(f"Generated links for file: {file_info['name']} ({file_info['size']} bytes) for user {message.from_user.id}")
                
            except FloodWait as e:
                logger.warning(f"FloodWait: {e.value} seconds")
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error in fdl_command: {e}", exc_info=True)
                await message.reply_text(
                    "❌ **An error occurred while processing your request.**\n\n"
                    "Please try again in a few moments. If the problem persists, "
                    "contact support with the error details."
                )
        
        @self.bot.on_callback_query()
        async def handle_callbacks(client: Client, callback_query):
            """Handle inline keyboard callbacks"""
            try:
                data = callback_query.data
                
                if data == "help":
                    help_text = (
                        "📖 **Quick Help**\n\n"
                        "1. Send or forward a file\n"
                        "2. Reply to it with `/dl`\n"
                        "3. Get download links!\n\n"
                        "Supported: Videos, Audio, Documents"
                    )
                    await callback_query.answer(help_text, show_alert=True)
                
                elif data == "about":
                    about_text = (
                        "ℹ️ **About File-to-Link Bot**\n\n"
                        "🚀 High-performance Telegram file linking service\n"
                        "⚡ Built with Pyrogram + AIOHTTP\n"
                        "🔒 Secure and efficient file streaming\n"
                        "📱 Mobile-friendly interface\n\n"
                        "Version: 1.0.0"
                    )
                    await callback_query.answer(about_text, show_alert=True)
                
            except Exception as e:
                logger.error(f"Error in callback handler: {e}")
                await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)
    
    async def start(self):
        """Start the bot and web server"""
        try:
            # Validate configuration
            if not Config.validate():
                logger.error("❌ Configuration validation failed. Please check your environment variables.")
                return
            
            # Setup handlers
            await self.setup_handlers()
            
            # Start the bot
            await self.bot.start()
            bot_info = await self.bot.get_me()
            logger.info(f"🤖 Bot started successfully: @{bot_info.username}")
            
            # Start web server
            self.web_runner = await start_web_server(self.bot)
            
            logger.info("✅ File-to-Link Bot is fully operational!")
            logger.info(f"🔗 Web server: {Config.BASE_URL}")
            logger.info("📱 Bot is ready to handle /dl commands")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("🛑 Received shutdown signal")
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.web_runner:
                await self.web_runner.cleanup()
                logger.info("🧹 Web server cleaned up")
            
            if self.bot.is_connected:
                await self.bot.stop()
                logger.info("🧹 Bot stopped")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    """Main entry point"""
    bot = FileLinkBot()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown completed")
