# VisuAIze 🎬

> **AI-Powered Step-by-Step Problem Solving & Video Tutorial Engine**  
> *Transform any question or complex problem into a structured, narrated Google Flow presentation tutorial video.*

---

## 🌟 Key Features

- 🧠 **Multi-AI Brain Support**: Select from **Groq (Ultra-fast Llama 3.3)**, **Google Gemini**, **Hugging Face Inference**, or **100% Local & Offline Ollama**.
- 📊 **Google Flow Presentation Engine**: Renders crisp, dark glassmorphism tutorial slides with step counter pills, hero typography, structured takeaways, and dynamic progress bars.
- 🎙️ **Neural Voice Narration**: Automated, natural human-like voiceovers synchronized with each step.
- 🎨 **Claude-Inspired Web UI**: Interactive model selector dropdown, suggestion chips, live SSE progress tracker, embedded video player, and 1-click MP4 downloading.
- 🔒 **100% Privacy & Zero Cloud Cost**: Supports running completely offline with local Ollama models.

---

## 🏗️ Architecture Pipeline

```
[User Problem / Question]
          │
          ▼
[Pass 1: AI Scripting Engine]       (ai_provider.py)    → Generates 5-8 structured steps with narration & scene prompts
          │
          ▼
[Pass 2: Google Flow Slide Engine]  (image_generator.py) → Renders high-definition presentation cards & step pills
          │
          ▼
[Pass 3: Neural Voice Synthesis]    (voice_generator.py) → Synthesizes voiceovers for each step, intro & outro
          │
          ▼
[Pass 4: Video Compositing]         (video_assembler.py) → Encodes smooth slide transitions, step badges & MP4 output
          │
          ▼
[Pass 5: Delivery & Playback]       (server.py)          → Browser player + 1-click MP4 download
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and add your preferred API keys:
```bash
copy .env.example .env
```

*(Note: If using **Ollama**, no API keys are required!)*

### 3. Launch the Web Application
```bash
python server.py
```
The browser will automatically open at `http://127.0.0.1:5000`.

---

## 🦙 Using Free Offline AI (Ollama)

To run VisuAIze 100% locally and free:
1. Install [Ollama](https://ollama.com).
2. Download a lightweight local model in your terminal:
   ```bash
   ollama run llama3.2
   ```
3. In VisuAIze, select **Ollama (Local)** in the model selector dropdown and start generating tutorial videos offline!

---

## 📦 Project Structure

```
visuAlze/
├── server.py             # Flask Web Server + SSE progress stream
├── ai_provider.py        # Multi-AI Engine (Groq, Gemini, HF, Ollama)
├── image_generator.py    # Google Flow Presentation Slide Generator
├── voice_generator.py    # Neural TTS Voiceover Engine
├── video_assembler.py    # MoviePy / FFmpeg Video Compositor
├── templates/
│   └── index.html        # Claude-style Web UI
├── static/
│   ├── css/style.css     # Modern dark glassmorphism styling
│   └── js/app.js         # Frontend controller & SSE listener
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
└── output/               # Rendered MP4 tutorial videos
```

---

## 📄 License
MIT License. Created for VisuAIze.
