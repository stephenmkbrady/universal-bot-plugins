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
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml

from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform
import sys
import os
# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from platform_services import AudioProcessingService


class STTAudioProcessingService(AudioProcessingService):
    """Audio processing service implementation using OpenAI Whisper"""
    
    def __init__(self, stt_plugin, logger=None):
        super().__init__(logger)
        self.stt_plugin = stt_plugin
    
    async def is_available(self) -> bool:
        """Check if audio processing is available"""
        return self.stt_plugin.config.get("openai", {}).get("api_key") is not None
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "name": "OpenAI Whisper Audio Processing",
            "version": "1.0.0",
            "capabilities": ["speech_to_text", "audio_transcription"],
            "supported_formats": self.stt_plugin.config.get("processing", {}).get("supported_formats", []),
            "available": True
        }
    
    async def process_audio_file(self, file_path: str, context: Dict[str, Any]) -> Optional[str]:
        """Process audio file and return transcribed text"""
        try:
            # Use the plugin's existing transcription logic
            return await self.stt_plugin._transcribe_audio_file(file_path)
        except Exception as e:
            self.logger.error(f"Audio processing failed: {e}")
            return None
    
    async def get_supported_formats(self) -> List[str]:
        """Get supported audio formats"""
        return self.stt_plugin.config.get("processing", {}).get("supported_formats", [])
    
    async def estimate_processing_time(self, file_size: int) -> float:
        """Estimate processing time based on file size"""
        # Rough estimate: 1 second per MB
        return file_size / (1024 * 1024)


class UniversalSTTOpenAIPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("stt_openai", logger=logger)
        self.version = "1.0.0"
        self.description = "Automatic speech-to-text using OpenAI Whisper API with 2x tempo processing"
        
        # Universal plugin - supports all platforms with audio capability
        self.supported_platforms = []  # Empty list means universal
        
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
    
    async def _on_initialize(self) -> bool:
        """Initialize the plugin"""
        try:
            self.logger.info(f"Initializing STT OpenAI plugin for {self.adapter.platform.value} platform")
            
            # Test OpenAI connection (non-blocking)
            try:
                if await self._test_openai_connection():
                    self.logger.info("✅ OpenAI Whisper API connection successful")
                else:
                    self.logger.warning("⚠️ OpenAI API not accessible - STT features will be limited")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not test OpenAI connection: {e}")
            
            # Register audio processing service if service registry is available
            if hasattr(self, 'service_registry') and self.service_registry:
                try:
                    audio_service = STTAudioProcessingService(self, self.logger)
                    self.service_registry.register_service("audio_processing", audio_service)
                    self.logger.info("✅ Registered audio processing service")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not register audio service: {e}")
            else:
                self.logger.warning("⚠️ Service registry not available - audio service not registered")
            
            self.logger.info("✅ STT OpenAI plugin initialized successfully (universal mode)")
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
                #return False
            
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
                        #return False
                        
        except Exception as e:
            self.logger.error(f"❌ Failed to test OpenAI connection: {e}")
            #return False
    
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
    
    async def handle_downloaded_audio(self, filename: str, file_path: str, user_name: str, chat_id: str, message_data: Dict[str, Any] = None) -> Optional[str]:
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
                transcribed_text = transcription_result.get('text', '').strip()
                
                # Check for voice commands first
                voice_response = None
                if transcribed_text and message_data:
                    voice_response = await self._process_voice_command(transcribed_text, user_name, message_data)
                
                # If voice command was processed, return that response
                if voice_response:
                    self.logger.info(f"🎤 STT PLUGIN: Voice command processed for {filename}")
                    return voice_response
                
                # Otherwise, return standard transcription
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
    
    # Voice Commands Implementation
    
    def _is_admin_user(self, contact_name: str) -> bool:
        """Check if user is admin based on admin_config.yml"""
        try:
            # Check if we have access to admin manager through adapter
            if hasattr(self.adapter, 'admin_manager'):
                return self.adapter.admin_manager.is_admin(contact_name)
            
            # Fallback: Try to load admin config directly
            admin_config_path = Path(__file__).parent.parent.parent.parent / "admin_config.yml"
            if admin_config_path.exists():
                with open(admin_config_path, 'r') as f:
                    admin_config = yaml.safe_load(f)
                    admins = admin_config.get('admins', [])
                    return contact_name in admins
            
            #return False
        except Exception as e:
            self.logger.error(f"Error checking admin status: {e}")
            #return False
    
    def _detect_wake_word(self, text: str) -> Optional[str]:
        """Detect wake word and return remaining command text"""
        text_lower = text.lower().strip()
        
        # Load wake words from config
        wake_words = self.config.get("voice_commands", {}).get("wake_words", ["ok bot", "hey bot", "bot"])
        
        for wake_word in wake_words:
            if text_lower.startswith(wake_word):
                # Remove wake word and return remaining text
                command_text = text_lower[len(wake_word):].strip()
                # Also remove leading comma and punctuation
                command_text = re.sub(r'^[,.:;!?]+\s*', '', command_text)
                if command_text:  # Ensure there's something after wake word
                    return command_text
        
        return None
    
    def _get_available_commands(self) -> List[str]:
        """Get all available commands from loaded plugins"""
        try:
            commands = []
            
            self.logger.info(f"🎤 COMMANDS: Starting command discovery...")
            
            # Get plugin manager from adapter's bot instance
            if hasattr(self.adapter, 'bot_instance'):
                self.logger.info(f"🎤 COMMANDS: Found bot_instance")
                if hasattr(self.adapter.bot_instance, 'plugin_manager'):
                    plugin_manager = self.adapter.bot_instance.plugin_manager
                    self.logger.info(f"🎤 COMMANDS: Found plugin_manager with {len(plugin_manager.plugins)} plugins")
                    
                    # Query all loaded plugins for their commands
                    for plugin_name, plugin in plugin_manager.plugins.items():
                        if hasattr(plugin, 'get_commands'):
                            plugin_commands = plugin.get_commands()
                            self.logger.info(f"🎤 COMMANDS: Plugin '{plugin_name}' provides commands: {plugin_commands}")
                            for cmd in plugin_commands:
                                commands.append(f"!{cmd}")
                        else:
                            self.logger.info(f"🎤 COMMANDS: Plugin '{plugin_name}' has no get_commands method")
                else:
                    self.logger.warning(f"🎤 COMMANDS: No plugin_manager found on bot_instance")
            else:
                self.logger.warning(f"🎤 COMMANDS: No bot_instance found on adapter")
            
            # Add some basic commands that are always available
            basic_commands = ["!status", "!help", "!contacts", "!groups"]
            for cmd in basic_commands:
                if cmd not in commands:
                    commands.append(cmd)
            
            self.logger.info(f"🎤 COMMANDS: Final command list: {commands}")
            return commands
            
        except Exception as e:
            self.logger.error(f"🎤 COMMANDS: Error getting available commands: {e}")
            import traceback
            self.logger.error(f"🎤 COMMANDS: Full traceback: {traceback.format_exc()}")
            return ["!status", "!help"]  # Fallback to basic commands
    
    async def _call_openrouter_llm(self, prompt: str, model: str) -> Optional[str]:
        """Call OpenRouter LLM with given prompt and model"""
        try:
            llm_config = self.config.get("voice_commands", {}).get("llm", {})
            api_key = llm_config.get("api_key", "")
            
            if not api_key:
                self.logger.error("No OpenRouter API key configured")
                return None
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": llm_config.get("max_tokens", 50),
                "temperature": llm_config.get("temperature", 0.1)
            }
            
            timeout = aiohttp.ClientTimeout(total=llm_config.get("timeout", 10))
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("choices") and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            return content.strip()
                    else:
                        error_text = await response.text()
                        self.logger.error(f"OpenRouter API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error calling OpenRouter LLM: {e}")
            return None
    
    async def _map_natural_language_to_command(self, text: str, available_commands: List[str]) -> Optional[str]:
        """Map natural language to bot command using LLM with fallbacks"""
        
        self.logger.info(f"🎤 LLM: Starting command mapping for text: '{text}'")
        self.logger.info(f"🎤 LLM: Available commands count: {len(available_commands)}")
        self.logger.info(f"🎤 LLM: Available commands: {available_commands}")
        
        # Early validation
        if not available_commands:
            self.logger.error("🎤 LLM: No available commands - cannot map")
            return None
            
        if not text or not text.strip():
            self.logger.error("🎤 LLM: Empty text - cannot map")
            return None
        
        # Build command list for prompt
        command_list = [f"- {cmd}" for cmd in available_commands]
        
        prompt = f"""Convert this natural language voice command to a bot command:
"{text}"

Available commands:
{chr(10).join(command_list)}

Return only the command exactly as shown, or "UNKNOWN" if no match:"""

        self.logger.info(f"🎤 LLM: Generated prompt length: {len(prompt)} chars")

        # Get models from config
        llm_config = self.config.get("voice_commands", {}).get("llm", {})
        primary_model = llm_config.get("primary_model", "google/gemini-2.0-flash-exp:free")
        fallback_models = llm_config.get("fallback_models", [
            "deepseek/deepseek-chat-v3-0324:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free"
        ])
        
        # Try primary model first, then fallbacks
        models_to_try = [primary_model] + fallback_models
        self.logger.info(f"🎤 LLM: Will try {len(models_to_try)} models: {models_to_try}")
        
        for i, model in enumerate(models_to_try, 1):
            try:
                self.logger.info(f"🎤 LLM: Attempting model {i}/{len(models_to_try)}: {model}")
                response = await self._call_openrouter_llm(prompt, model)
                self.logger.info(f"🎤 LLM: Model {model} response: '{response}'")
                
                if response and response != "UNKNOWN":
                    # Validate the response is a real command
                    if any(response.startswith(cmd) for cmd in available_commands):
                        self.logger.info(f"🎤 LLM: Successfully mapped using {model}: '{text}' → '{response}'")
                        return response
                    else:
                        self.logger.warning(f"🎤 LLM: Model {model} returned invalid command: '{response}'")
                else:
                    self.logger.warning(f"🎤 LLM: Model {model} returned UNKNOWN or empty response")
                    
            except Exception as e:
                self.logger.warning(f"🎤 LLM: {model} failed: {e}")
                continue  # Try next model
        
        self.logger.error("🎤 LLM: All models failed for command mapping")
        return None
    
    async def _execute_voice_command(self, command: str, contact_name: str, message_data: Dict[str, Any]) -> None:
        """Execute a voice command"""
        try:
            # Get command registry from adapter's bot instance
            if hasattr(self.adapter, 'bot_instance') and hasattr(self.adapter.bot_instance, 'command_registry'):
                command_registry = self.adapter.bot_instance.command_registry
                
                # Get plugin manager
                plugin_manager = None
                if hasattr(self.adapter.bot_instance, 'plugin_manager'):
                    plugin_manager = self.adapter.bot_instance.plugin_manager
                
                # Execute the command
                await command_registry.execute_command(command, contact_name, plugin_manager, message_data)
                
        except Exception as e:
            self.logger.error(f"Error executing voice command '{command}': {e}")
    
    async def _process_voice_command(self, transcribed_text: str, contact_name: str, message_data: Dict[str, Any]) -> Optional[str]:
        """Process transcribed text for voice commands"""
        try:
            # Check if voice commands are enabled
            voice_config = self.config.get("voice_commands", {})
            if not voice_config.get("enabled", False):
                return None
            
            # Check if user is admin (if admin_only is enabled)
            if voice_config.get("admin_only", True):
                if not self._is_admin_user(contact_name):
                    return None  # Silently ignore non-admin voice commands
            
            # Wake word detection
            command_text = self._detect_wake_word(transcribed_text)
            if not command_text:
                return None
            
            self.logger.info(f"🎤 VOICE: Wake word detected from {contact_name}: '{command_text}'")
            
            # Get available commands dynamically
            available_commands = self._get_available_commands()
            self.logger.info(f"🎤 VOICE: Available commands: {available_commands}")
            
            # Map to command using LLM with fallbacks
            mapped_command = await self._map_natural_language_to_command(command_text, available_commands)
            
            if mapped_command and mapped_command != "UNKNOWN":
                self.logger.info(f"🎤 VOICE: Command mapped: '{command_text}' → '{mapped_command}'")
                
                # Execute the command
                await self._execute_voice_command(mapped_command, contact_name, message_data)
                
                return f"🎤 Voice command executed: {mapped_command}"
            else:
                self.logger.warning(f"🎤 VOICE: Command not recognized: '{command_text}'")
                return f"🎤 Voice command not recognized: '{command_text}'"
            
        except Exception as e:
            self.logger.error(f"Error processing voice command: {e}")
            return None