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

# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class FileServer:
    """File server class for basic streaming and downloads"""
    
    def __init__(self, bot_client: Client):
        self.bot = bot_client
        self.file_cache = {}  # In-memory cache for file metadata
        self.media_processor = MediaProcessor()
        
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from Telegram"""
        try:
            # Try to get file info from cache first
            if file_id in self.file_cache:
                cached_info = self.file_cache[file_id]
                # Check if cache is still valid (10 minutes)
                if time.time() - cached_info['cached_at'] < 600:
                    return cached_info['data']
            
            # Get file from Telegram
            message = await self.bot.get_messages(
                chat_id=int(file_id.split('_')[0]),
                message_ids=int(file_id.split('_')[1])
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
        """Optimized file streaming with adaptive chunk sizing"""
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

            # Get optimized streaming settings
            stream_settings = self.media_processor.get_streaming_optimization_settings(
                file_info['file_name'], file_info['file_size']
            )

            # Get optimized streaming headers
            headers = self.media_processor.get_optimized_streaming_headers(
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
                return await self._handle_range_request_optimized(request, response, file_info, range_header, stream_settings)

            await response.prepare(request)

            # Adaptive streaming with optimized chunk sizes
            await self._adaptive_stream_file(response, file_info, stream_settings)

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
            stream_url = f"/stream/{file_id}/{filename}" if filename else f"/stream/{file_id}"
            download_url = f"/download/{file_id}/{filename}" if filename else f"/download/{file_id}"
            
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
            
            # Generate HTML player page
            html_content = self._generate_player_html(
                display_name, file_size, stream_url, download_url, is_video, is_audio, compatibility_info
            )
            
            return web.Response(text=html_content, content_type='text/html')
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating web player for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    def _generate_player_html(self, filename: str, file_size: str, stream_url: str,
                            download_url: str, is_video: bool, is_audio: bool, compatibility_info: dict) -> str:
        """Generate HTML for the optimized web player with better buffering"""

        # Get proper MIME type and streaming settings
        mime_type = compatibility_info['mime_type']
        compatibility = compatibility_info['compatibility']

        # Get streaming optimization settings for the file
        stream_settings = self.media_processor.get_streaming_optimization_settings(filename, 0)  # Size not needed for player
        preload_strategy = stream_settings['preload_strategy']

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

        # Determine player type and optimized settings
        if is_video:
            player_element = f'''
                <video id="mediaPlayer" controls preload="{preload_strategy}" style="width: 100%; max-width: 600px; height: auto;"
                       playsinline webkit-playsinline>
                    <source src="{stream_url}" type="{mime_type}">
                    Your browser does not support this video format. <a href="{download_url}">Download the file</a> to play it with a media player.
                </video>
            '''
            media_icon = "🎬"
            media_type = "Video"
        else:  # is_audio
            player_element = f'''
                <audio id="mediaPlayer" controls preload="{preload_strategy}" style="width: 100%; max-width: 400px;">
                    <source src="{stream_url}" type="{mime_type}">
                    Your browser does not support this audio format. <a href="{download_url}">Download the file</a> to play it with a media player.
                </audio>
            '''
            media_icon = "🎵"
            media_type = "Audio"
        
        html_template = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
            max-width: 800px;
            width: 100%;
        }}
        
        .header {{
            margin-bottom: 30px;
        }}
        
        .file-icon {{
            font-size: 3rem;
            margin-bottom: 15px;
        }}
        
        .file-name {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 10px;
            word-break: break-word;
        }}
        
        .file-info {{
            font-size: 1rem;
            opacity: 0.8;
            margin-bottom: 5px;
        }}
        
        .player-container {{
            margin: 30px 0;
            display: flex;
            justify-content: center;
        }}
        
        video, audio {{
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .controls {{
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 30px;
        }}
        
        .btn {{
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        
        .btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        
        .btn-primary {{
            background: rgba(74, 144, 226, 0.8);
            border-color: rgba(74, 144, 226, 1);
        }}
        
        .btn-primary:hover {{
            background: rgba(74, 144, 226, 1);
        }}
        
        .footer {{
            margin-top: 30px;
            font-size: 0.9rem;
            opacity: 0.7;
        }}
        
        .compatibility-warning {{
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            font-size: 0.9rem;
            text-align: left;
        }}
        
        .compatibility-info {{
            background: rgba(23, 162, 184, 0.2);
            border: 1px solid rgba(23, 162, 184, 0.5);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            font-size: 0.9rem;
            text-align: left;
        }}
        
        .download-link {{
            color: #ffd700;
            text-decoration: underline;
        }}
        
        .download-link:hover {{
            color: #ffed4e;
        }}
        
        .format-info {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 10px;
            margin: 15px 0;
            font-size: 0.85rem;
            opacity: 0.8;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
                margin: 10px;
            }}
            
            .file-name {{
                font-size: 1.2rem;
            }}
            
            video, audio {{
                max-width: 100% !important;
            }}
            
            .controls {{
                flex-direction: column;
                align-items: center;
            }}
            
            .btn {{
                width: 200px;
                justify-content: center;
            }}
        }}
        
        @media (max-width: 480px) {{
            .container {{
                padding: 15px;
                margin: 5px;
            }}
            
            .file-name {{
                font-size: 1.1rem;
            }}
            
            .file-icon {{
                font-size: 2.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="file-icon">{media_icon}</div>
            <div class="file-name">{filename}</div>
            <div class="file-info">{media_type} • {file_size}</div>
        </div>
        
        <div class="format-info">
            📄 <strong>Format:</strong> {mime_type.split('/')[-1].upper()} • 
            🌐 <strong>Browser Support:</strong> {compatibility.title()}
        </div>
        
        {compatibility_warning}
        
        <div class="player-container">
            {player_element}
        </div>
        
        <div class="controls">
            <a href="{download_url}" class="btn btn-primary">
                📥 Download
            </a>
            <a href="{stream_url}" class="btn" target="_blank">
                🔗 Direct Link
            </a>
            <button onclick="copyToClipboard('{stream_url}')" class="btn">
                📋 Copy Link
            </button>
        </div>
        
        <div class="footer">
            <p>🤖 Powered by Telegram File-to-Link Bot</p>
        </div>
    </div>
    
    <script>
        function copyToClipboard(text) {{
            const fullUrl = window.location.origin + text;
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            // Method 1: Try modern clipboard API (works on HTTPS)
            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(fullUrl).then(function() {{
                    showCopySuccess(btn, originalText);
                }}).catch(function(err) {{
                    console.warn('Clipboard API failed, trying fallback:', err);
                    fallbackCopyToClipboard(fullUrl, btn, originalText);
                }});
            }} else {{
                // Method 2: Use fallback for HTTP or unsupported browsers
                fallbackCopyToClipboard(fullUrl, btn, originalText);
            }}
        }}
        
        function fallbackCopyToClipboard(text, btn, originalText) {{
            // Create a temporary textarea element
            const textArea = document.createElement("textarea");
            textArea.value = text;
            
            // Make it invisible but still selectable
            textArea.style.position = "fixed";
            textArea.style.top = "0";
            textArea.style.left = "0";
            textArea.style.width = "2em";
            textArea.style.height = "2em";
            textArea.style.padding = "0";
            textArea.style.border = "none";
            textArea.style.outline = "none";
            textArea.style.boxShadow = "none";
            textArea.style.background = "transparent";
            textArea.style.opacity = "0";
            
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {{
                // Try the older execCommand method
                const successful = document.execCommand('copy');
                if (successful) {{
                    showCopySuccess(btn, originalText);
                }} else {{
                    showManualCopyDialog(text);
                }}
            }} catch (err) {{
                console.error('Fallback copy failed:', err);
                showManualCopyDialog(text);
            }}
            
            document.body.removeChild(textArea);
        }}
        
        function showCopySuccess(btn, originalText) {{
            btn.innerHTML = '✅ Copied!';
            btn.style.background = 'rgba(46, 204, 113, 0.8)';
            
            setTimeout(() => {{
                btn.innerHTML = originalText;
                btn.style.background = '';
            }}, 2000);
        }}
        
        function showManualCopyDialog(text) {{
            // Create a modal dialog for manual copying
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(30, 30, 30, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                padding: 25px;
                z-index: 10000;
                max-width: 90%;
                width: 500px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            `;
            
            modal.innerHTML = `
                <div style="color: white; text-align: center;">
                    <h3 style="margin: 0 0 15px 0; font-size: 1.2rem;">📋 Copy Link</h3>
                    <p style="margin: 0 0 15px 0; opacity: 0.9; font-size: 0.9rem;">
                        Select and copy the link below:
                    </p>
                    <input type="text" value="${{text}}" readonly style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid rgba(255, 255, 255, 0.3);
                        border-radius: 8px;
                        background: rgba(255, 255, 255, 0.1);
                        color: white;
                        font-family: monospace;
                        font-size: 0.85rem;
                        margin-bottom: 15px;
                        cursor: text;
                    " onclick="this.select();" id="copyInput">
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        <button onclick="
                            document.getElementById('copyInput').select();
                            document.execCommand('copy');
                            this.innerHTML = '✅ Copied!';
                            this.style.background = 'rgba(46, 204, 113, 0.8)';
                            setTimeout(() => {{
                                document.body.removeChild(this.closest('div').parentElement);
                            }}, 1500);
                        " style="
                            background: rgba(74, 144, 226, 0.8);
                            border: 1px solid rgba(74, 144, 226, 1);
                            color: white;
                            padding: 8px 20px;
                            border-radius: 20px;
                            cursor: pointer;
                            font-weight: 500;
                            transition: all 0.3s ease;
                        " onmouseover="this.style.background='rgba(74, 144, 226, 1)'" 
                          onmouseout="this.style.background='rgba(74, 144, 226, 0.8)'">
                            Copy
                        </button>
                        <button onclick="document.body.removeChild(this.closest('div').parentElement);" style="
                            background: rgba(255, 255, 255, 0.2);
                            border: 1px solid rgba(255, 255, 255, 0.3);
                            color: white;
                            padding: 8px 20px;
                            border-radius: 20px;
                            cursor: pointer;
                            font-weight: 500;
                            transition: all 0.3s ease;
                        " onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" 
                          onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            Close
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Auto-select the text in the input
            const input = document.getElementById('copyInput');
            if (input) {{
                input.focus();
                input.select();
            }}
        }}
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            const player = document.getElementById('mediaPlayer');
            if (!player) return;
            
            switch(e.code) {{
                case 'Space':
                    e.preventDefault();
                    if (player.paused) {{
                        player.play();
                    }} else {{
                        player.pause();
                    }}
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    player.currentTime = Math.max(0, player.currentTime - 10);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    player.currentTime = Math.min(player.duration, player.currentTime + 10);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    player.volume = Math.min(1, player.volume + 0.1);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    player.volume = Math.max(0, player.volume - 0.1);
                    break;
            }}
        }});
        
        // Enhanced buffering and streaming optimization
        const player = document.getElementById('mediaPlayer');
        let bufferingIndicator = null;
        let bufferingStartTime = 0;

        function createBufferingIndicator() {{
            if (bufferingIndicator) return;

            bufferingIndicator = document.createElement('div');
            bufferingIndicator.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-size: 0.9rem;
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 1000;
                pointer-events: none;
            `;
            bufferingIndicator.innerHTML = `
                <div class="spinner" style="
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-top: 2px solid white;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                "></div>
                <span>Buffering...</span>
            `;

            // Add spinner animation
            const style = document.createElement('style');
            style.textContent = `
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            `;
            document.head.appendChild(style);

            const container = document.querySelector('.player-container');
            if (container) {{
                container.style.position = 'relative';
                container.appendChild(bufferingIndicator);
            }}
        }}

        function removeBufferingIndicator() {{
            if (bufferingIndicator) {{
                bufferingIndicator.remove();
                bufferingIndicator = null;
            }}
        }}

        if (player) {{
            // Enhanced loading and buffering events
            player.addEventListener('loadstart', function() {{
                console.log('Loading started...');
                createBufferingIndicator();
                bufferingStartTime = Date.now();
            }});

            player.addEventListener('canplay', function() {{
                console.log('Can start playing');
                removeBufferingIndicator();
                const loadTime = Date.now() - bufferingStartTime;
                console.log(`Media loaded in ${{loadTime}}ms`);
            }});

            player.addEventListener('waiting', function() {{
                console.log('Buffering...');
                createBufferingIndicator();
                bufferingStartTime = Date.now();
            }});

            player.addEventListener('playing', function() {{
                console.log('Playing...');
                removeBufferingIndicator();
                if (bufferingStartTime > 0) {{
                    const bufferTime = Date.now() - bufferingStartTime;
                    console.log(`Buffered in ${{bufferTime}}ms`);
                    bufferingStartTime = 0;
                }}
            }});

            player.addEventListener('progress', function() {{
                // Log buffering progress
                if (player.buffered.length > 0) {{
                    const buffered = player.buffered.end(player.buffered.length - 1);
                    const duration = player.duration || 1;
                    const bufferPercent = (buffered / duration) * 100;
                    console.log(`Buffered: ${{bufferPercent.toFixed(1)}}%`);
                }}
            }});

            player.addEventListener('stalled', function() {{
                console.warn('Stream stalled, attempting to recover...');
                // Force a small seek to restart streaming
                setTimeout(() => {{
                    const currentTime = player.currentTime;
                    player.currentTime = currentTime + 0.1;
                    player.currentTime = currentTime;
                }}, 1000);
            }});

            player.addEventListener('error', function(e) {{
                console.error('Media error:', e);
                removeBufferingIndicator();
                const errorCode = player.error ? player.error.code : 'unknown';
                let errorMessage = 'Error loading media. ';

                switch(errorCode) {{
                    case 1:
                        errorMessage += 'The media loading was aborted.';
                        break;
                    case 2:
                        errorMessage += 'A network error occurred. Please check your connection.';
                        break;
                    case 3:
                        errorMessage += 'The media format is not supported by your browser.';
                        break;
                    case 4:
                        errorMessage += 'The media source is not suitable.';
                        break;
                    default:
                        errorMessage += 'An unknown error occurred.';
                }}

                errorMessage += ' Please try downloading the file to play it with a media player like VLC.';

                // Show error message in the player container
                const container = document.querySelector('.player-container');
                if (container) {{
                    container.innerHTML = `
                        <div style="background: rgba(220, 53, 69, 0.2); border: 1px solid rgba(220, 53, 69, 0.5);
                                    border-radius: 10px; padding: 20px; text-align: center;">
                            <div style="font-size: 2rem; margin-bottom: 10px;">❌</div>
                            <div style="font-weight: 600; margin-bottom: 10px;">Playback Error</div>
                            <div style="font-size: 0.9rem; margin-bottom: 15px;">${{errorMessage}}</div>
                            <a href="{download_url}" class="btn btn-primary" style="text-decoration: none;">
                                📥 Download File
                            </a>
                        </div>
                    `;
                }}
            }});

            // Add connection quality monitoring
            let connectionCheckInterval = setInterval(() => {{
                if (player.networkState === HTMLMediaElement.NETWORK_LOADING) {{
                    console.log('Network loading...');
                }} else if (player.networkState === HTMLMediaElement.NETWORK_IDLE) {{
                    console.log('Network idle');
                }} else if (player.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) {{
                    console.warn('No source available');
                }}
            }}, 5000);

            // Cleanup on page unload
            window.addEventListener('beforeunload', () => {{
                if (connectionCheckInterval) {{
                    clearInterval(connectionCheckInterval);
                }}
                removeBufferingIndicator();
            }});
        }}
    </script>
</body>
</html>
        '''
        
        return html_template
    
    async def _adaptive_stream_file(self, response: web.StreamResponse, file_info: dict, stream_settings: dict):
        """Adaptive streaming with dynamic chunk sizing for optimal performance"""
        try:
            bytes_sent = 0
            buffer_sent = 0
            current_chunk_size = stream_settings['initial_chunk_size']
            max_chunk_size = min(stream_settings['max_chunk_size'], Config.MAX_CHUNK_SIZE)
            buffer_target = stream_settings['buffer_target']

            # Stream file with adaptive chunk sizes
            async for chunk in self.bot.stream_media(file_info['message'], limit=current_chunk_size):
                # Send chunk to client
                await response.write(chunk)
                chunk_size = len(chunk)
                bytes_sent += chunk_size
                buffer_sent += chunk_size

                # Dynamically adjust chunk size after building initial buffer
                if buffer_sent >= buffer_target and current_chunk_size < max_chunk_size:
                    # Scale up chunk size for better throughput after initial buffering
                    new_chunk_size = min(current_chunk_size * stream_settings['buffer_multiplier'], max_chunk_size)
                    if new_chunk_size != current_chunk_size:
                        current_chunk_size = new_chunk_size
                        logger.debug(f"Scaled chunk size to {current_chunk_size} bytes after {buffer_sent} bytes buffered")

                # Yield control to prevent blocking
                if bytes_sent % (1024 * 1024) == 0:  # Every 1MB
                    await asyncio.sleep(0)  # Allow other tasks to run

            await response.write_eof()

            # Log streaming statistics
            logger.info(f"Adaptive stream completed: {bytes_sent} bytes sent, final chunk size: {current_chunk_size} bytes for file: {file_info['file_name']}")

        except Exception as e:
            logger.error(f"Error in adaptive streaming: {e}")
            raise

    async def _handle_range_request_optimized(self, request: web.Request, response: web.StreamResponse,
                                            file_info: dict, range_header: str, stream_settings: dict) -> web.StreamResponse:
        """Optimized range request handling for video streaming with adaptive chunks"""
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

            # Add optimized headers for range requests
            optimized_headers = self.media_processor.get_optimized_streaming_headers(
                file_info['file_type'], file_info['file_name'], file_info['file_size'], range_request=True
            )
            for key, value in optimized_headers.items():
                if key not in response.headers:  # Don't override existing headers
                    response.headers[key] = value

            await response.prepare(request)

            # Use smaller chunks for range requests to improve seeking precision
            range_chunk_size = min(stream_settings['initial_chunk_size'], Config.INITIAL_CHUNK_SIZE)
            current_pos = 0
            bytes_sent = 0
            total_to_send = end - start + 1

            async for chunk in self.bot.stream_media(file_info['message'], limit=range_chunk_size):
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
                    await response.write(chunk_data)
                    bytes_sent += len(chunk_data)

                    # Break if we've sent all requested data
                    if bytes_sent >= total_to_send:
                        break

                current_pos += len(chunk)

            await response.write_eof()

            logger.debug(f"Optimized range request served: {bytes_sent} bytes ({start}-{end}) for file: {file_info['file_name']}")
            return response

        except Exception as e:
            logger.error(f"Error handling optimized range request: {e}")
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
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
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
