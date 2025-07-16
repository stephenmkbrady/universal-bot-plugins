# STT OpenAI Plugin

Automatic speech-to-text transcription using OpenAI Whisper API.

## Features

- **Automatic Transcription**: Automatically transcribes audio messages sent to the bot
- **OpenAI Whisper**: Uses OpenAI's state-of-the-art Whisper API for transcription
- **Multiple Formats**: Supports M4A, WAV, MP3, MP4, MPEG, MPGA, OGG, WEBM audio formats
- **File Size Limits**: Configurable maximum file size limits (25MB default for OpenAI)
- **Multi-language**: Automatic language detection or configurable language
- **Group & Direct Chat Support**: Properly routes transcriptions to correct chat location

## How It Works

1. **Audio Detection**: Plugin automatically detects audio files in messages
2. **Download**: Downloads audio via bot's XFTP system
3. **Transcription**: Sends audio to OpenAI Whisper API
4. **Response**: Posts transcription back to the same chat (group or direct)

## Installation

1. Place plugin files in `plugins/external/stt_openai/`
2. Configure OpenAI API key in `config.yaml`
3. Set `OPENAI_API_KEY` environment variable
4. Enable plugin in `plugins/plugin.yml`
5. Restart bot to load plugin

## Configuration

Edit `config.yaml` to configure the plugin:

```yaml
openai:
  # OpenAI API configuration
  api_key: ${OPENAI_API_KEY}  # Set in environment variables
  model: "whisper-1"          # OpenAI Whisper model
  timeout: 30                 # Request timeout in seconds
  language: "auto"            # Language (auto, en, es, fr, de, etc.)
  response_format: "json"     # Response format (json, text, srt, verbose_json, vtt)

# Processing settings
processing:
  max_file_size: 26214400     # Maximum file size in bytes (25MB for OpenAI)
  supported_formats: ["m4a", "wav", "mp3", "mp4", "mpeg", "mpga", "ogg", "webm"]
  temp_dir: "/tmp/stt_openai" # Temporary directory for audio processing
```

## Environment Variables

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Or in your `.env` file:
```
OPENAI_API_KEY=sk-...
```

## Plugin Configuration

Enable the plugin in `plugins/plugin.yml`:

```yaml
stt_openai:
  enabled: true  # STT plugin using OpenAI Whisper
```

## Commands

- `!stt` - Show STT status and configuration
- `!sttconfig` - Display detailed configuration
- `!transcribe` - Show transcription information

## Usage

### Automatic Transcription

1. Record audio message in SimpleX Chat
2. Send to bot (direct message or mention in group)
3. Bot automatically:
   - Detects audio file
   - Downloads via XFTP
   - Sends to OpenAI Whisper API
   - Posts transcription: "🎤 **Audio from username** 💬 \"transcribed text\""

### Example Output

```
🎤 **Audio from cosmic**

💬 "Hey bot, can you check the weather forecast for tomorrow?"
```

## Technical Details

### OpenAI Whisper API Integration

The plugin communicates with OpenAI's Whisper API using HTTP requests:

```
POST https://api.openai.com/v1/audio/transcriptions
Authorization: Bearer sk-...
Content-Type: multipart/form-data

{
  "file": <audio_file>,
  "model": "whisper-1",
  "language": "en",
  "response_format": "json"
}

Response:
{
  "text": "transcribed text",
  "usage": {
    "type": "duration",
    "seconds": 4
  }
}
```

### Audio File Processing

1. **Detection**: Checks file extension against supported formats
2. **Size Validation**: Enforces 25MB limit (OpenAI requirement)
3. **Download**: Uses bot's XFTP download system
4. **Direct Upload**: Sends original audio file directly to OpenAI (no processing)
5. **Cleanup**: No temporary files created - uses original downloaded file

### Chat Routing

The plugin properly routes messages based on context:
- **Group messages**: Transcription posted to the group
- **Direct messages**: Transcription posted to direct chat
- **Consistent routing**: Uses same logic as other bot features

### Error Handling

- **API Unavailable**: Falls back gracefully, logs error
- **Unsupported Format**: Silently ignores non-audio files
- **File Too Large**: Sends error message to user
- **Download Failed**: Logs error, notifies user
- **Transcription Failed**: Sends error message with details

## Integration Points

### Bot Integration

The plugin integrates with:
- **XFTP System**: For audio file downloads
- **Message Handler**: For automatic audio detection and routing
- **Universal Plugin System**: For command handling
- **Adapter System**: For cross-platform messaging

### OpenAI Integration

- **Whisper API**: Direct integration with OpenAI's Whisper API
- **Environment Variables**: Secure API key management
- **Usage Tracking**: OpenAI provides usage statistics in dashboard

## Security Considerations

- **API Key Security**: API key loaded from environment variables
- **File Size Limits**: Prevents DoS via large files (25MB OpenAI limit)
- **Format Validation**: Only processes known audio formats
- **No Local Storage**: Audio files not stored permanently
- **Secure Transmission**: HTTPS communication with OpenAI

## Performance Notes

- **Async Processing**: Non-blocking audio processing
- **Duplicate Prevention**: Prevents processing same file multiple times
- **Resource Management**: Configurable timeouts and size limits
- **Direct Upload**: No local audio processing reduces CPU usage
- **OpenAI Speed**: Fast transcription using OpenAI's optimized infrastructure

## Costs

- **OpenAI Pricing**: $0.006 per minute of audio transcribed
- **Usage Tracking**: Monitor costs in OpenAI dashboard
- **File Duration**: Billing based on original audio length

## Troubleshooting

### Common Issues

1. **"No OpenAI API key configured"**
   - Set `OPENAI_API_KEY` environment variable
   - Restart bot to reload environment

2. **"OpenAI API test failed"**
   - Check API key is valid
   - Verify network connectivity to OpenAI
   - Check OpenAI service status

3. **"Audio file too large"**
   - OpenAI has 25MB limit
   - Use compressed audio formats
   - Record shorter audio clips

4. **"Transcription failed"**
   - Check OpenAI API status
   - Verify audio format is supported
   - Check API key has credits

### Debug Logging

Enable debug logging to troubleshoot issues:
```yaml
logging:
  level: DEBUG
```

Look for log messages with `🎤 STT DEBUG:` prefix.

## Supported Audio Formats

OpenAI Whisper supports these formats:
- **M4A** (recommended for mobile)
- **WAV** (uncompressed)
- **MP3** (compressed)
- **MP4** (video with audio)
- **MPEG** (compressed)
- **MPGA** (MPEG audio)
- **OGG** (open source)
- **WEBM** (web format)

## Language Support

Whisper supports 99+ languages including:
- English (`en`)
- Spanish (`es`)
- French (`fr`)
- German (`de`)
- Italian (`it`)
- Portuguese (`pt`)
- Russian (`ru`)
- Japanese (`ja`)
- Korean (`ko`)
- Chinese (`zh`)
- And many more...

Set `language: "auto"` for automatic detection or specify a language code.

## Future Enhancements

- **Voice Command Processing**: Detect commands in transcribed text
- **Language Translation**: Transcribe and translate simultaneously
- **Speaker Identification**: Multi-speaker transcription
- **Custom Prompts**: Custom system prompts for domain-specific transcription
- **Batch Processing**: Process multiple audio files together