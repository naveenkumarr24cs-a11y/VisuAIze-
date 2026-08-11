# VisuAIze 🎬🧠

> **Turn any topic into a step-by-step visual learning video — powered by multi-model AI.**

VisuAIze is an open-source AI-powered educational video generator. Type any topic, question, or concept and the system automatically understands your intent, builds a structured learning curriculum, generates visual scenes, narrates with dual human voices, and produces a complete tutorial video — all in minutes.

---

## ✨ Features

- 🧠 **Universal AI Intent Engine** — Understands any topic instantly. Type `"Java"`, `"Photosynthesis"`, `"Quantum Entanglement"`, `"How to invest"` — no clarification needed.
- 📚 **AI Pedagogy Engine** — Automatically structures content into a 3-arc learning script: Problem Hook → Analogy Bridge → Step-by-Step Solution.
- 🎙️ **Dual-Voice Narration** — Teacher & Student dialogue voices powered by gTTS for a real tutoring experience.
- 🎨 **7 Visual Styles** — Classic, Whiteboard, Kawaii, Watercolor, Papercraft, Retro Print, Heritage.
- 🎬 **Automated Video Assembly** — Scenes, narration, and visuals are assembled into a full MP4 video using MoviePy.
- 💬 **Conversational Chat Interface** — Claude/ChatGPT-style session history with full restore and multi-turn context.
- ☁️ **Firebase Cloud Sync** — Chat sessions and video history synced to Firebase Realtime Database.
- 🔒 **100% Offline Mode** — Works completely offline with Ollama (no internet required).
- 🔄 **Multi-Provider AI** — Switch between Groq, Gemini, HuggingFace, or Ollama from the UI.

---

## 🖼️ Video Styles

| Style | Description |
|---|---|
| **Classic** | Clean dark presentation — professional and minimal |
| **Whiteboard** | Hand-drawn marker on white board feel |
| **Kawaii** | Cute anime-inspired pastel aesthetic |
| **Watercolor** | Soft watercolor painting style |
| **Papercraft** | Cut-paper collage design |
| **Retro Print** | Vintage halftone and grain texture |
| **Heritage** | Classical grid notebook aesthetic |

---

## 🤖 AI Providers

| Provider | Model | Mode | API Key Required |
|---|---|---|---|
| **Groq** | Llama 3.3 70B | ☁️ Cloud | ✅ Yes (Free) |
| **Google Gemini** | Gemini 2.0 Flash | ☁️ Cloud | ✅ Yes (Free) |
| **HuggingFace** | Llama 3.1 8B Instruct | ☁️ Cloud | ✅ Yes (Free) |
| **Ollama** | llama3.2 (or any installed model) | 🔒 Offline | ❌ No |

---

## 🏗️ Architecture

```
User Input (Any Topic)
        │
        ▼
┌─────────────────────┐
│   Intent Engine     │  ← Classifies intent: NEW_VIDEO / MODIFY / CHAT
│   (intent_engine.py)│  ← Synthesizes a structured tutorial title
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Pedagogy Engine    │  ← Generates 3-arc structured learning script
│ (pedagogy_engine.py)│  ← Problem Hook → Analogy Bridge → Solution Steps
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Dual Voice Engine  │  ← Teacher + Student dialogue synthesis
│(dual_voice_engine.py)│ ← gTTS narration for each scene
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Image Generator    │  ← Generates per-scene visual frames
│ (image_generator.py)│  ← Applies chosen visual style (Pillow rendering)
│  Style Renderer     │
│ (style_renderer.py) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Video Assembler    │  ← Combines frames + audio into final MP4
│(video_assembler.py) │  ← MoviePy clip concatenation & multiplexing
└─────────┬───────────┘
          │
          ▼
      Final MP4 Video
```

---

## 📁 Project Structure

```
visuAlze/
├── server.py               # Flask web server & REST API
├── intent_engine.py        # AI intent classification & topic synthesis
├── pedagogy_engine.py      # 3-arc learning script generator
├── ai_provider.py          # Multi-model AI provider (Groq/Gemini/HF/Ollama)
├── dual_voice_engine.py    # Dual-speaker narration engine
├── voice_generator.py      # gTTS voice synthesis
├── image_generator.py      # Per-scene visual frame generator
├── style_renderer.py       # 7 visual style renderers (Pillow)
├── video_assembler.py      # MoviePy video assembly & audio sync
├── firebase_manager.py     # Firebase Realtime DB sync manager
├── main.py                 # CLI entry point
├── static/
│   ├── css/style.css       # App styling
│   ├── js/app.js           # Frontend chat & video UI logic
│   └── img/                # App icons & assets
├── templates/
│   └── index.html          # Main web UI template
├── output/                 # Generated videos saved here
├── temp/                   # Temporary frames & audio clips
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .gitignore
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- pip
- (Optional) [Ollama](https://ollama.com) for offline mode

### 1. Clone the Repository

```bash
git clone https://github.com/naveenkumarr24cs-a11y/VisuAIze-.git
cd VisuAIze-
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```env
# Choose your AI provider: groq | gemini | huggingface | ollama
AI_PROVIDER=groq

# API Keys (get free keys from each provider)
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Ollama (No API key needed — local offline only)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Output directories
OUTPUT_DIR=output
TEMP_DIR=temp

# Firebase (Optional — for cloud sync)
FIREBASE_SERVICE_ACCOUNT=firebase_service_account.json
FIREBASE_DATABASE_URL=https://your-app-default-rtdb.firebaseio.com/
FIREBASE_PROJECT_ID=your-firebase-project-id
```

### 4. Run the App

```bash
python server.py
```

The app will open automatically at **http://127.0.0.1:5000**

---

## 🔑 Getting Free API Keys

| Provider | Get Key | Free Tier |
|---|---|---|
| **Groq** | [console.groq.com](https://console.groq.com) | ✅ Free (generous limits) |
| **Google Gemini** | [aistudio.google.com](https://aistudio.google.com) | ✅ Free (1500 req/day) |
| **HuggingFace** | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | ✅ Free |
| **Ollama** | [ollama.com](https://ollama.com) | ✅ Free + Offline |

---

## 🔒 Running Fully Offline with Ollama

```bash
# Install Ollama
winget install Ollama.Ollama   # Windows
# or visit https://ollama.com for Mac/Linux

# Pull a model (one-time, ~4GB)
ollama run llama3.2

# Set in .env
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

Then start the app normally. No internet connection required.

---

## 🚀 How to Use

1. Open **http://127.0.0.1:5000** in your browser
2. Type any topic in the chat input — e.g., `"Explain recursion"`, `"How does DNA work?"`, `"Binary search algorithm"`
3. Choose a **Visual Style** (Classic, Whiteboard, Kawaii, etc.)
4. Toggle **Dual-Voice** narration on/off
5. Press **Enter** or click **Send**
6. Watch the AI generate your video step-by-step
7. Download or replay the finished MP4 video

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask |
| **AI Models** | Groq (Llama 3.3 70B), Google Gemini 2.0 Flash, HuggingFace (Llama 3.1 8B), Ollama |
| **Text-to-Speech** | gTTS (Google Text-to-Speech), pyttsx3 |
| **Image Generation** | Pillow (PIL) — custom style renderers |
| **Video Assembly** | MoviePy 1.0.3 |
| **Frontend** | HTML5, Vanilla CSS, Vanilla JavaScript |
| **Cloud Sync** | Firebase Realtime Database |
| **Environment** | python-dotenv |

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main web UI |
| `POST` | `/api/generate` | Generate video from topic input |
| `GET` | `/api/status/<job_id>` | Server-Sent Events stream for job progress |
| `GET` | `/api/history` | Fetch all past sessions |
| `GET` | `/api/providers` | List available AI providers |
| `GET` | `/video/<filename>` | Serve a generated MP4 video |
| `GET` | `/api/firebase/status` | Firebase sync connection status |
| `POST` | `/api/firebase/sync` | Manually trigger Firebase cloud sync |

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to your branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 👨‍💻 Author

**Naveen Kumar**
- GitHub: [@naveenkumarr24cs-a11y](https://github.com/naveenkumarr24cs-a11y)

---

<p align="center">
  <i>Built with ❤️ — making learning visual, structured, and accessible for everyone.</i>
</p>
