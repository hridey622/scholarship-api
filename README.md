# Scholarship Form-Filling API

A production-ready FastAPI web service that converts voice/text input into structured scholarship form data and automates form submission.

## Features

- 🎤 **Speech-to-Text**: Upload audio files for transcription via Bhashini API
- 🤖 **LLM Extraction**: Intelligent data extraction using Ollama/Llama 3.2
- 📝 **Session Management**: Multi-step conversation tracking with automatic expiration
- 🌐 **Form Automation**: Headless Chrome form filling with screenshots
- 📸 **Screenshot Capture**: Visual verification of filled forms

## Quick Start

### Prerequisites

- Python 3.10+
- Chrome browser (for Selenium)
- Ollama with `llama3.2:3b` model

### Installation

```bash
# Navigate to project directory
cd scholarship_api

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file and edit
copy .env.example .env
```

### Start Ollama (if not running)

```bash
ollama serve
ollama pull llama3.2:3b
```

### Run the API

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access API Documentation

Open http://localhost:8000/docs in your browser.

## API Endpoints

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session/start` | POST | Create new session |
| `/session/{id}` | GET | Get session status |
| `/session/{id}/questions` | GET | Get current question group |
| `/session/{id}/text` | POST | Submit text answer |
| `/session/{id}/audio` | POST | Submit audio file |
| `/session/{id}/data` | GET | Get all extracted data |
| `/session/{id}/skip` | POST | Skip current questions |
| `/session/{id}` | DELETE | Delete session |

### Form Filling

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/form/{id}/preview` | GET | Preview form data |
| `/form/{id}/fill` | POST | Fill the form |
| `/form/{id}/status` | GET | Get filling status |
| `/form/{id}/screenshot` | GET | Get form screenshot |

## Usage Example

### 1. Start a Session

```bash
curl -X POST http://localhost:8000/session/start
```

Response:
```json
{
  "session_id": "abc123-...",
  "status": "active",
  "current_group_index": 0,
  "total_groups": 4
}
```

### 2. Get Questions

```bash
curl http://localhost:8000/session/{session_id}/questions
```

### 3. Submit Answer (Text)

```bash
curl -X POST http://localhost:8000/session/{session_id}/text \
  -H "Content-Type: application/json" \
  -d '{"text": "My name is John Doe, I am male, from Delhi, Hindu"}'
```

### 4. Submit Answer (Audio)

```bash
curl -X POST http://localhost:8000/session/{session_id}/audio \
  -F "audio=@recording.wav"
```

### 5. Fill Form

```bash
curl -X POST http://localhost:8000/form/{session_id}/fill
```

### 6. Get Screenshot

```bash
curl http://localhost:8000/form/{session_id}/screenshot --output form.png
```

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f api
```

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BHASHINI_URL` | (Bhashini API URL) | Speech API endpoint |
| `BHASHINI_KEY` | - | API key for Bhashini |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | LLM model name |
| `SESSION_TIMEOUT_MINUTES` | `30` | Session expiry time |
| `FORM_URL` | (Scholarship URL) | Target form URL |

## Important Notes

⚠️ **CAPTCHA**: The scholarship website has CAPTCHA that cannot be automated. After form filling, manual CAPTCHA completion is required.

⚠️ **API Key**: Store the Bhashini API key securely in production.

⚠️ **Ollama**: Ensure Ollama is running with the required model before starting the API.

## License

MIT License
