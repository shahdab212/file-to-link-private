"""
AIOHTTP Web Server for Telegram File-to-Link Bot
Handles file streaming and download requests
"""

import asyncio
import logging
import os
import sys
import mimetypes
from typing import Optional, Dict, Any
from aiohttp import web, ClientSession
from aiohttp.web_response import StreamResponse
from pyrogram import Client
from pyrogram.types import Message
import hashlib
import time
from pathlib import Path
from urllib.parse import unquote
import json

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from utils.media_utils import MediaProcessor
from utils.crypto_utils import CryptoUtils

# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class FileServer:
    """File server class for basic streaming and downloads"""
    
    def __init__(self, bot_client: Client):
        self.bot = bot_client
        self.file_cache = {}  # In-memory cache for file metadata
        self.media_processor = MediaProcessor()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes
                current_time = time.time()
                expired_keys = [
                    k for k, v in self.file_cache.items() 
                    if current_time - v['cached_at'] > 3600  # Expire after 1 hour
                ]
                
                for key in expired_keys:
                    del self.file_cache[key]
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
                await asyncio.sleep(60)

    async def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from Telegram"""
        try:
            # Try to get file info from cache first
            if file_id in self.file_cache:
                cached_info = self.file_cache[file_id]
                # Check if cache is still valid (10 minutes)
                if time.time() - cached_info['cached_at'] < 600:
                    return cached_info['data']
            
            # Try to decrypt ID, otherwise treat as legacy raw ID (backward compatibility)
            decrypted_id = CryptoUtils.decrypt_id(file_id)
            target_id = decrypted_id if decrypted_id else file_id
            
            try:
                chat_id_str, message_id_str = target_id.split('_')
                chat_id = int(chat_id_str)
                message_id = int(message_id_str)
            except ValueError:
                # Invalid ID format
                logger.warning(f"Invalid file ID format: {file_id} (decrypted: {decrypted_id})")
                return None

            # Get file from Telegram
            message = await self.bot.get_messages(
                chat_id=chat_id,
                message_ids=message_id
            )
            
            if not message or not (message.document or message.video or message.audio or message.photo):
                return None
            
            # Extract file metadata
            file_info = self.media_processor.extract_file_metadata(message)
            file_info['message'] = message
            
            # Cache the file info
            self.file_cache[file_id] = {
                'data': file_info,
                'cached_at': time.time()
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {e}")
            return None
    
    async def stream_file(self, request: web.Request) -> web.StreamResponse:
        """File streaming with basic features"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # If no filename in URL, redirect to URL with filename
            if not filename:
                from urllib.parse import quote
                safe_filename = quote(file_info['file_name'], safe='')
                redirect_url = f"/stream/{file_id}/{safe_filename}"
                raise web.HTTPFound(location=redirect_url)
            
            # Get streaming headers
            headers = self.media_processor.get_streaming_headers(
                file_info['file_type'], 
                file_info['file_name'], 
                file_info['file_size']
            )
            
            # Prepare response
            response = web.StreamResponse()
            for key, value in headers.items():
                response.headers[key] = value
            
            # Handle range requests for video streaming
            range_header = request.headers.get('Range')
            if range_header:
                return await self._handle_range_request(request, response, file_info, range_header)
            
            await response.prepare(request)
            
            # Stream file in chunks
            bytes_sent = 0
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                await response.write(chunk)
                bytes_sent += len(chunk)
            
            await response.write_eof()
            
            # Log streaming statistics
            logger.info(f"Streamed {bytes_sent} bytes for file: {file_info['file_name']}")
            
            return response
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error streaming file {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def download_file(self, request: web.Request) -> web.StreamResponse:
        """Download file with proper filename handling"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # If no filename in URL, redirect to URL with filename
            if not filename:
                from urllib.parse import quote
                safe_filename = quote(file_info['file_name'], safe='')
                redirect_url = f"/download/{file_id}/{safe_filename}"
                raise web.HTTPFound(location=redirect_url)
            
            # Use provided filename or original filename
            download_filename = unquote(filename) if filename else file_info['file_name']
            safe_filename = self.media_processor.generate_safe_filename(download_filename)
            
            # Prepare download response
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Length'] = str(file_info['file_size'])
            response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response.headers['Cache-Control'] = 'no-cache'
            
            await response.prepare(request)
            
            # Stream file in chunks
            bytes_sent = 0
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                await response.write(chunk)
                bytes_sent += len(chunk)
            
            await response.write_eof()
            
            # Log download statistics
            logger.info(f"Downloaded {bytes_sent} bytes for file: {safe_filename}")
            
            return response
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def direct_link(self, request: web.Request) -> web.Response:
        """Direct link with filename for better compatibility"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Redirect to stream URL with proper filename
            stream_url = f"/stream/{file_id}/{filename}" if filename else f"/stream/{file_id}"
            raise web.HTTPFound(location=stream_url)
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating direct link for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def playlist(self, request: web.Request) -> web.Response:
        """Generate M3U playlist for external players"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Generate stream URL
            if filename:
                from urllib.parse import quote
                safe_filename = quote(filename, safe='')
                stream_url = f"{Config.BASE_URL}/stream/{file_id}/{safe_filename}"
            else:
                stream_url = f"{Config.BASE_URL}/stream/{file_id}"
                
            # Content of M3U file
            m3u_content = f"#EXTM3U\n#EXTINF:-1,{filename or file_info['file_name']}\n{stream_url}"
            
            return web.Response(
                text=m3u_content, 
                content_type='audio/x-mpegurl',
                headers={'Content-Disposition': f'attachment; filename="playlist.m3u"'}
            )
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating playlist for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")

    async def web_player(self, request: web.Request) -> web.Response:
        """Web player interface for streaming files"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Get file details
            display_name = unquote(filename) if filename else file_info['file_name']
            file_size = self.media_processor.format_file_size(file_info['file_size'])
            # Create Safe/Absolute URLs
            from urllib.parse import quote
            safe_filename = quote(display_name, safe='')
            
            # Absolute URL for external players and copy link
            absolute_stream_url = f"{Config.BASE_URL}/stream/{file_id}/{safe_filename}"
            
            # Relative URL for internal player (keeps it cleaner, but could use absolute too)
            stream_url = f"/stream/{file_id}/{safe_filename}"
            download_url = f"/download/{file_id}/{safe_filename}"
            
            # Check if file is streamable using proper detection
            is_streamable = self.media_processor.is_streamable(display_name, file_info.get('mime_type'))
            is_video = file_info['file_type'] == 'video' or (is_streamable and 'video' in file_info.get('mime_type', ''))
            is_audio = file_info['file_type'] == 'audio' or (is_streamable and 'audio' in file_info.get('mime_type', ''))
            
            # Always show web player for streamable files, even if Telegram detected them as documents
            if not is_streamable:
                # For non-streamable files, redirect to download
                raise web.HTTPFound(location=download_url)
            
            # Get browser compatibility info
            compatibility_info = self.media_processor.get_browser_compatibility_info(display_name)
            
            # Generate VLC URL (Android intent)
            vlc_url = Config.get_vlc_android_url(file_id, display_name)
            # Generate VLC URL (Desktop - vlc:// scheme with absolute URL)
            # This avoids the "playlist download" issue by passing the direct link to VLC if handlers are set up
            vlc_desktop_url = f"vlc://{absolute_stream_url}"
            
            # Generate HTML player page
            html_content = self._generate_player_html(
                display_name, file_size, absolute_stream_url, download_url, is_video, is_audio, compatibility_info, vlc_url, vlc_desktop_url
            )
            
            return web.Response(
                text=html_content, 
                content_type='text/html',
                headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
            )
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating web player for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    def _generate_player_html(self, filename: str, file_size: str, stream_url: str, 
                            download_url: str, is_video: bool, is_audio: bool, compatibility_info: dict, 
                            vlc_url: str, vlc_desktop_url: str) -> str:
        """Generate HTML for the web player"""
        
        # Get proper MIME type
        mime_type = compatibility_info['mime_type']
        compatibility = compatibility_info['compatibility']
        
        # Generate compatibility warning if needed
        compatibility_warning = ""
        if compatibility == 'low':
            compatibility_warning = f'''
                <div class="compatibility-warning">
                    ⚠️ <strong>Limited Browser Support:</strong> This format may not play in all browsers. 
                    <a href="{download_url}" class="download-link">Download the file</a> to play with a media player like VLC.
                </div>
            '''
        elif compatibility == 'moderate':
            compatibility_warning = f'''
                <div class="compatibility-info">
                    ℹ️ <strong>Note:</strong> This format has moderate browser support. 
                    If it doesn't play, try <a href="{download_url}" class="download-link">downloading</a> the file.
                </div>
            '''
        
        # Determine player type and settings
        if is_video:
            player_element = f'''
                <video id="mediaPlayer" controls preload="metadata" style="width: 100%; max-width: 600px; height: auto;">
                    <source src="{stream_url}" type="{mime_type}">
                    Your browser does not support this video format. <a href="{download_url}">Download the file</a> to play it with a media player.
                </video>
            '''
            media_icon = "🎬"
            media_type = "Video"
        else:  # is_audio
            player_element = f'''
                <audio id="mediaPlayer" controls preload="metadata" style="width: 100%; max-width: 400px;">
                    <source src="{stream_url}" type="{mime_type}">
                    Your browser does not support this audio format. <a href="{download_url}">Download the file</a> to play it with a media player.
                </audio>
            '''
            media_icon = "🎵"
            media_type = "Audio"
        
        # Load template
        try:
            template_path = Path(__file__).parent / 'templates' / 'player.html'
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Use simple string replacement to avoid issues with CSS/JS curly braces
            html = template
            html = html.replace('{filename}', filename)
            html = html.replace('{media_icon}', media_icon)
            html = html.replace('{media_type}', media_type)
            html = html.replace('{file_size}', file_size)
            html = html.replace('{mime_type_short}', mime_type.split('/')[-1].upper()) # Added this line to replace mime_type_short
            html = html.replace('{compatibility}', compatibility.title())
            html = html.replace('{compatibility_warning}', compatibility_warning)
            html = html.replace('{player_element}', player_element)
            html = html.replace('{download_url}', download_url)
            html = html.replace('{download_url}', download_url)
            html = html.replace('{download_url}', download_url)
            html = html.replace('{stream_url}', stream_url)
            html = html.replace('{vlc_url}', vlc_url)
            html = html.replace('{vlc_desktop_url}', vlc_desktop_url)
            
            return html
            
        except Exception as e:
            logger.error(f"Error loading player template: {e}")
            return f"Error loading player template: {e}"
    
    async def _handle_range_request(self, request: web.Request, response: web.StreamResponse, 
                                  file_info: dict, range_header: str) -> web.StreamResponse:
        """Range request handling for video streaming"""
        try:
            # Parse range header
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_info['file_size'] - 1
            
            # Validate range
            if start >= file_info['file_size'] or end >= file_info['file_size'] or start > end:
                response.set_status(416)  # Range Not Satisfiable
                response.headers['Content-Range'] = f'bytes */{file_info["file_size"]}'
                await response.prepare(request)
                return response
            
            # Set partial content headers
            response.set_status(206)  # Partial Content
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_info["file_size"]}'
            response.headers['Content-Length'] = str(end - start + 1)
            
            await response.prepare(request)
            
            # Stream the requested range
            current_pos = 0
            bytes_sent = 0
            
            # Smart Chunking: Use smaller limit for small range requests (like probing)
            request_size = end - start + 1
            chunk_limit = min(Config.CHUNK_SIZE, max(1024 * 256, request_size)) if request_size < Config.CHUNK_SIZE else Config.CHUNK_SIZE
            
            async for chunk in self.bot.stream_media(file_info['message'], limit=chunk_limit):
                chunk_end = current_pos + len(chunk)
                
                # Skip chunks before the requested range
                if chunk_end <= start:
                    current_pos = chunk_end
                    continue
                
                # Stop if we've passed the requested range
                if current_pos > end:
                    break
                
                # Trim chunk to fit the requested range
                chunk_start = max(0, start - current_pos)
                chunk_end_trim = min(len(chunk), end - current_pos + 1)
                
                if chunk_start < chunk_end_trim:
                    chunk_data = chunk[chunk_start:chunk_end_trim]
                    try:
                        await response.write(chunk_data)
                        bytes_sent += len(chunk_data)
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                        # Client disconnected (normal during seeking/pausing)
                        return response
                
                current_pos += len(chunk)
            
            try:
                await response.write_eof()
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass
            
            logger.debug(f"Range request served: {bytes_sent} bytes ({start}-{end})")
            return response
            
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
             # Top level catch for connection issues
             return response
        except Exception as e:
            if "Cannot write to closing transport" in str(e):
                # Specific aiohttp error that matches the logs
                return response
            logger.error(f"Error handling range request: {e}")
            raise web.HTTPInternalServerError(text="Range request error")

async def create_app(bot_client: Client) -> web.Application:
    """Create and configure the AIOHTTP application"""
    app = web.Application()
    app['bot_client'] = bot_client
    file_server = FileServer(bot_client)
    
    # Basic file routes
    app.router.add_get('/stream/{file_id}', file_server.stream_file)
    app.router.add_get('/stream/{file_id}/{filename}', file_server.stream_file)
    app.router.add_get('/download/{file_id}', file_server.download_file)
    app.router.add_get('/download/{file_id}/{filename}', file_server.download_file)
    app.router.add_get('/direct/{file_id}/{filename}', file_server.direct_link)
    app.router.add_get('/play/{file_id}', file_server.web_player)
    app.router.add_get('/play/{file_id}/{filename}', file_server.web_player)
    app.router.add_get('/playlist/{file_id}', file_server.playlist)
    app.router.add_get('/playlist/{file_id}/{filename}', file_server.playlist)
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({
            "status": "healthy", 
            "service": "telegram-file-bot",
            "version": "1.0.0",
            "features": [
                "file_streaming",
                "file_download",
                "direct_links"
            ]
        })
    
    async def root_page(request):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bot Status</title>
            <style>
                body { font-family: system-ui, sans-serif; background: #121212; color: #4CAF50; display: flex; height: 100vh; justify-content: center; align-items: center; margin: 0; }
                .status { text-align: center; }
                h1 { font-size: 3rem; margin-bottom: 10px; }
                p { color: #aaa; }
                .pulse { width: 15px; height: 15px; background: #4CAF50; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; margin-left: 10px; }
                @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); } 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); } }
            </style>
        </head>
        <body>
            <div class="status">
                <h1>Bot is Running<div class="pulse"></div></h1>
                <p>Telegram File-to-Link Service is Operational</p>
                <p style="font-size: 0.8rem; margin-top: 20px;">PING OK</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/', root_page)
    
    return app

async def start_web_server(bot_client: Client):
    """Start the web server"""
    app = await create_app(bot_client)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, Config.HOST, Config.PORT)
    await site.start()
    
    logger.info(f"🚀 Web server started on {Config.HOST}:{Config.PORT}")
    logger.info(f"🔗 Base URL: {Config.BASE_URL}")
    logger.info(f"📥 Download URL format: {Config.BASE_URL}/download/{{file_id}}/{{filename}}")
    logger.info(f"📺 Stream URL format: {Config.BASE_URL}/stream/{{file_id}}/{{filename}}")
    logger.info(f"🔗 Direct URL format: {Config.BASE_URL}/direct/{{file_id}}/{{filename}}")
    
    return runner
