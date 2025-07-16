"""
Universal STT OpenAI Plugin - Speech-to-Text using OpenAI Whisper

This plugin automatically processes audio messages sent to the bot by:
1. Detecting audio files in messages
2. Downloading them via XFTP
3. Doubling the tempo of the audio (2x speed)
4. Sending processed audio to OpenAI Whisper API
5. Posting transcription back to the chat

Supports OpenAI Whisper API for speech-to-text services.
"""

import aiohttp
import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml

from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalSTTOpenAIPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("stt_openai", logger=logger)
        self.version = "1.0.0"
        self.description = "Automatic speech-to-text using OpenAI Whisper API with 2x tempo processing"
        
        # Enable for SimpleX platform
        self.supported_platforms = [BotPlatform.SIMPLEX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Load configuration
        self.config = self._load_config()
        
        # Audio processing state
        self.processing_audio = set()  # Track files being processed to avoid duplicates
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent / "config.yaml"
            self.logger.info(f"🔍 Looking for STT OpenAI config at: {config_path}")
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Expand environment variables
                config = self._expand_env_vars(config)
                
                self.logger.info("✅ STT OpenAI configuration loaded successfully")
                return config
            else:
                self.logger.warning("❌ No config.yaml found, using defaults")
                return self._get_default_config()
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": "whisper-1",
                "timeout": 30,
                "language": "auto",
                "response_format": "json"
            },
            "processing": {
                "max_file_size": 26214400,  # 25MB
                "supported_formats": ["m4a", "wav", "mp3", "mp4", "mpeg", "mpga", "ogg", "webm"],
                "temp_dir": "/tmp/stt_openai",
                "tempo_multiplier": 2.0  # Double the tempo
            }
        }
    
    def _expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively expand environment variables in config"""
        import re
        
        def expand_value(value):
            if isinstance(value, str):
                # Replace ${VAR_NAME} with environment variable value
                def replace_env_var(match):
                    var_name = match.group(1)
                    return os.getenv(var_name, match.group(0))  # Keep original if not found
                
                return re.sub(r'\$\{([^}]+)\}', replace_env_var, value)
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            else:
                return value
        
        return expand_value(config)
    
    async def initialize(self, adapter) -> bool:
        """Initialize the plugin"""
        try:
            self.logger.info("Initializing STT OpenAI plugin for simplex platform")
            
            # Test OpenAI connection
            if await self._test_openai_connection():
                self.logger.info("✅ OpenAI Whisper API connection successful")
            else:
                self.logger.error("❌ Failed to connect to OpenAI API - STT features will be limited")
            
            self.logger.info("STT OpenAI plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize STT OpenAI plugin: {e}")
            return False
    
    async def _test_openai_connection(self) -> bool:
        """Test connection to OpenAI API"""
        try:
            api_key = self.config["openai"]["api_key"]
            if not api_key:
                self.logger.error("❌ No OpenAI API key configured")
                return False
            
            # Test with a simple request to models endpoint
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.openai.com/v1/models", headers=headers) as response:
                    if response.status == 200:
                        self.logger.info("✅ OpenAI API connection successful")
                        return True
                    else:
                        self.logger.error(f"❌ OpenAI API test failed with status {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Failed to test OpenAI connection: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["transcribe", "stt", "sttconfig"]
    
    async def handle_command(self, context: CommandContext) -> str:
        """Handle plugin commands"""
        if context.command == "transcribe" or context.command == "stt":
            return "🎤 STT is enabled - just send an audio message and I'll transcribe it automatically!"
        elif context.command == "sttconfig":
            return self._get_stt_config_info()
        else:
            return f"Unknown command: {context.command}"
    
    def _get_stt_config_info(self) -> str:
        """Get STT configuration information"""
        config = self.config["openai"]
        processing = self.config["processing"]
        
        return f"""🎤 **STT OpenAI Configuration**
**Model:** {config['model']}
**Language:** {config['language']}
**Response Format:** {config['response_format']}
**Tempo Multiplier:** {processing['tempo_multiplier']}x
**Max File Size:** {processing['max_file_size'] / (1024*1024):.1f} MB
**Supported Formats:** {', '.join(processing['supported_formats'])}
**Timeout:** {config['timeout']} seconds"""
    
    async def handle_downloaded_audio(self, filename: str, file_path: str, user_name: str, chat_id: str) -> Optional[str]:
        """Handle downloaded audio file for transcription"""
        try:
            self.logger.info(f"🎤 STT PLUGIN: handle_downloaded_audio called for {filename}")
            
            # Create unique processing ID
            processing_id = f"{filename}_{int(time.time() * 1000)}"
            
            # Check if already processing
            if processing_id in self.processing_audio:
                self.logger.info(f"🎤 STT PLUGIN: {filename} already being processed")
                return None
            
            # Add to processing set
            self.processing_audio.add(processing_id)
            self.logger.info(f"🎤 STT PLUGIN: Added {processing_id} to processing queue")
            
            # Send processing message
            self.logger.info(f"🎤 STT PLUGIN: Sending processing message...")
            
            # Start transcription
            self.logger.info(f"🎤 STT PLUGIN: Starting transcription...")
            transcription_result = await self._transcribe_audio(file_path)
            
            if transcription_result:
                response = self._format_transcription(transcription_result, user_name)
                self.logger.info(f"🎤 STT PLUGIN: Transcription successful for {filename}")
                return response
            else:
                self.logger.error(f"🎤 STT PLUGIN: Transcription failed for {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"🎤 STT PLUGIN: Error processing {filename}: {e}")
            return None
        finally:
            # Remove from processing set
            if processing_id in self.processing_audio:
                self.processing_audio.remove(processing_id)
                self.logger.info(f"🎤 STT PLUGIN: Removed {processing_id} from processing queue")
    
    async def _process_audio_tempo(self, input_path: str) -> Optional[str]:
        """Process audio to double the tempo using ffmpeg"""
        try:
            # Create temporary directory
            temp_dir = Path(self.config["processing"]["temp_dir"])
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temp file for processed audio (keep as M4A)
            temp_processed = temp_dir / f"tempo_processed_{os.getpid()}_{int(time.time())}.m4a"
            
            # Get tempo multiplier from config
            tempo_multiplier = self.config["processing"]["tempo_multiplier"]
            
            # Use ffmpeg to double the tempo while maintaining pitch and format
            import subprocess
            cmd = [
                'ffmpeg', '-i', input_path,
                '-filter:a', f'atempo={tempo_multiplier}',  # Double tempo
                '-c:a', 'aac',   # Keep AAC codec for M4A
                '-y',            # Overwrite output
                str(temp_processed)
            ]
            
            self.logger.info(f"🎤 STT DEBUG: Processing audio with {tempo_multiplier}x tempo")
            self.logger.info(f"🎤 STT DEBUG: ffmpeg command: {' '.join(cmd)}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            self.logger.info(f"🎤 STT DEBUG: ffmpeg return code: {result.returncode}")
            self.logger.info(f"🎤 STT DEBUG: ffmpeg stdout: {stdout.decode()}")
            self.logger.info(f"🎤 STT DEBUG: ffmpeg stderr: {stderr.decode()}")
            
            if result.returncode == 0:
                self.logger.info(f"🎤 STT DEBUG: Audio tempo processing successful")
                self.logger.info(f"🎤 STT DEBUG: Processed file exists: {os.path.exists(temp_processed)}")
                if os.path.exists(temp_processed):
                    self.logger.info(f"🎤 STT DEBUG: Processed file size: {os.path.getsize(temp_processed)} bytes")
                return str(temp_processed)
            else:
                self.logger.error(f"🎤 STT DEBUG: Audio tempo processing failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            self.logger.error(f"🎤 STT: Error processing audio tempo: {e}")
            return None
    
    async def _transcribe_audio(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Transcribe audio file using OpenAI Whisper API"""
        processed_file = None
        try:
            self.logger.info(f"🎤 STT DEBUG: Starting transcription for {file_path}")
            
            api_key = self.config["openai"]["api_key"]
            self.logger.info(f"🎤 STT DEBUG: API key configured: {bool(api_key)}")
            
            if not api_key:
                self.logger.error("❌ No OpenAI API key configured")
                return None
            
            # Check file size
            file_size = os.path.getsize(file_path)
            max_size = self.config["processing"]["max_file_size"]
            self.logger.info(f"🎤 STT DEBUG: File size: {file_size} bytes (max: {max_size})")
            
            if file_size > max_size:
                self.logger.error(f"❌ Audio file too large: {file_size} bytes (max: {max_size})")
                return None
            
            # Check file format
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            supported_formats = self.config["processing"]["supported_formats"]
            self.logger.info(f"🎤 STT DEBUG: File extension: {file_ext}, supported: {supported_formats}")
            
            if file_ext not in supported_formats:
                self.logger.error(f"❌ Unsupported audio format: {file_ext}")
                return None
            
            # Use original audio file directly
            processed_file = file_path
            self.logger.info(f"🎤 STT DEBUG: Using original audio file: {processed_file}")
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            data = {
                "model": self.config["openai"]["model"],
                "language": self.config["openai"]["language"] if self.config["openai"]["language"] != "auto" else None,
                "response_format": self.config["openai"]["response_format"]
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Send file to OpenAI
            self.logger.info(f"🎤 STT DEBUG: Sending processed audio to OpenAI Whisper API...")
            self.logger.info(f"🎤 STT DEBUG: Request data: {data}")
            self.logger.info(f"🎤 STT DEBUG: Headers: Authorization header present: {bool(headers.get('Authorization'))}")
            
            async with aiohttp.ClientSession() as session:
                with open(processed_file, 'rb') as audio_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('file', audio_file, filename=os.path.basename(processed_file))
                    
                    for key, value in data.items():
                        form_data.add_field(key, str(value))
                    
                    self.logger.info(f"🎤 STT DEBUG: Making POST request to OpenAI...")
                    
                    async with session.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers=headers,
                        data=form_data,
                        timeout=aiohttp.ClientTimeout(total=self.config["openai"]["timeout"])
                    ) as response:
                        self.logger.info(f"🎤 STT DEBUG: OpenAI response status: {response.status}")
                        
                        if response.status == 200:
                            result = await response.json()
                            self.logger.info(f"🎤 STT DEBUG: OpenAI transcription successful")
                            self.logger.info(f"🎤 STT DEBUG: Transcription result: {result}")
                            return result
                        else:
                            error_text = await response.text()
                            self.logger.error(f"❌ OpenAI API error {response.status}: {error_text}")
                            self.logger.error(f"🎤 STT DEBUG: Full error response: {error_text}")
                            return None
                            
        except Exception as e:
            self.logger.error(f"❌ Error transcribing audio: {e}")
            import traceback
            self.logger.error(f"🎤 STT DEBUG: Full traceback: {traceback.format_exc()}")
            return None
        finally:
            # No cleanup needed since we're using the original file
            pass
    
    def _format_transcription(self, transcription: Dict[str, Any], user_name: str) -> str:
        """Format transcription result for display"""
        text = transcription.get('text', '').strip()
        
        if not text:
            return f"🎤 **Audio from {user_name}**\\n\\n🔇 (No speech detected)"
        
        # Format with user name and transcription
        return f"🎤 **Audio from {user_name}**\\n\\n💬 \"{text}\""
    
    async def cleanup(self):
        """Clean up plugin resources"""
        try:
            # Clean up any remaining temporary files
            temp_dir = Path(self.config["processing"]["temp_dir"])
            if temp_dir.exists():
                for temp_file in temp_dir.glob("tempo_processed_*"):
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to clean up temp file {temp_file}: {e}")
            
            self.logger.info("STT OpenAI plugin cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during STT OpenAI plugin cleanup: {e}")