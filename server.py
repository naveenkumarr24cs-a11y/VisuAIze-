"""
VisuAIze - Web Application Server & History Manager
Provides browser UI for generating and browsing step-by-step instructional videos.
Supports full session restoration (Claude/ChatGPT style chat interface).
"""

import json
import os
import queue
import shutil
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file

load_dotenv()

# ── App Setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "visualize-secret-key-2026"

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "temp"))
UPLOAD_DIR = Path("uploads")
HISTORY_FILE = OUTPUT_DIR / "sessions.json"

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# Active job progress queues: job_id → Queue of SSE events
_job_queues: dict[str, queue.Queue] = {}
_job_status: dict[str, dict] = {}


# ── History Helpers ──────────────────────────────────────────────────────────

def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_history(sessions: list[dict]):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save history: {e}")


def _add_session(session_data: dict):
    sessions = _load_history()
    # Prepend new session
    sessions = [s for s in sessions if s.get("filename") != session_data.get("filename")]
    sessions.insert(0, session_data)
    _save_history(sessions[:50])


# ── Pipeline Runner ──────────────────────────────────────────────────────────

def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _run_pipeline(job_id: str, question: str, provider: str, image_path: str | None):
    q = _job_queues[job_id]

    def push(phase: int, total: int, message: str, detail: str = ""):
        pct = int((phase / total) * 100)
        q.put({"type": "progress", "phase": phase, "total": total,
               "pct": pct, "message": message, "detail": detail})

    try:
        os.environ["AI_PROVIDER"] = provider

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c for c in question[:30] if c.isalnum() or c in " _-").strip().replace(" ", "_")
        session = f"{timestamp}_{safe}"

        tmp_images = TEMP_DIR / session / "images"
        tmp_audio = TEMP_DIR / session / "audio"
        tmp_images.mkdir(parents=True, exist_ok=True)
        tmp_audio.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / f"{session}.mp4")

        # Phase 1 – AI Scripting
        push(1, 4, f"Generating steps with {provider.title()} AI...", "Analyzing your question")
        from ai_provider import generate_steps
        steps = generate_steps(question, image_path)
        push(1, 4, f"Script ready ({len(steps)} steps)!", ", ".join(s["title"] for s in steps[:3]) + "...")

        # Phase 2 – Realistic Google Flow Visuals (Parallel)
        push(2, 4, "Building Google Flow visual slides...", f"Generating {len(steps)} high-definition visual slides in parallel")
        from image_generator import generate_all_images
        image_paths = generate_all_images(steps, str(tmp_images))
        push(2, 4, "All visual slides ready!", f"{len(image_paths)} visual slides generated")

        # Phase 3 – Voice Narrations (Synchronized)
        push(3, 4, "Recording studio voice narrations...", f"Creating {len(steps) + 2} synchronized audio clips")
        from voice_generator import generate_all_voices
        audio_data = generate_all_voices(steps, str(tmp_audio))
        push(3, 4, "Voice narrations synchronized!", "All audio clips created")

        # Phase 4 – Video Assembly (Ultrafast)
        push(4, 4, "Assembling 1080p video...", "Stitching visual slides, voice & Ken Burns motion")
        from video_assembler import assemble_video
        assemble_video(steps=steps, image_paths=image_paths,
                       audio_data=audio_data, output_path=output_path, topic=question)

        # Cleanup temp
        shutil.rmtree(TEMP_DIR / session, ignore_errors=True)

        file_size = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
        video_filename = Path(output_path).name

        # Save session to history
        session_record = {
            "id": session,
            "question": question,
            "provider": provider,
            "steps": steps,
            "filename": video_filename,
            "size_mb": file_size,
            "created": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        }
        _add_session(session_record)

        _job_status[job_id] = {"status": "done", "filename": video_filename,
                                "size_mb": file_size, "steps": len(steps), "session": session_record}
        q.put({"type": "done", "filename": video_filename,
               "size_mb": file_size, "steps": len(steps), "session": session_record})

    except Exception as e:
        import traceback
        err = str(e)
        tb = traceback.format_exc()
        _job_status[job_id] = {"status": "error", "error": err}
        q.put({"type": "error", "error": err, "traceback": tb})


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           current_provider=os.getenv("AI_PROVIDER", "groq"))


@app.route("/api/generate", methods=["POST"])
def api_generate():
    question = request.form.get("question", "").strip()
    provider = request.form.get("provider", os.getenv("AI_PROVIDER", "groq")).strip()
    image_file = request.files.get("image")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    image_path = None
    if image_file and image_file.filename:
        save_path = UPLOAD_DIR / image_file.filename
        image_file.save(str(save_path))
        image_path = str(save_path)

    job_id = f"job_{int(time.time() * 1000)}"
    _job_queues[job_id] = queue.Queue()
    _job_status[job_id] = {"status": "running"}

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, question, provider, image_path),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def api_progress(job_id):
    if job_id not in _job_queues:
        return jsonify({"error": "Job not found"}), 404

    def event_stream():
        q = _job_queues[job_id]
        while True:
            try:
                event = q.get(timeout=30)
                yield _sse_event(event)
                if event.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield _sse_event({"type": "ping"})

    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/history")
def api_history():
    """Returns all past chat/video sessions."""
    saved = _load_history()
    existing_files = {f.name for f in OUTPUT_DIR.glob("*.mp4")}

    # Filter only files that still exist on disk
    valid_sessions = [s for s in saved if s.get("filename") in existing_files]

    # If some mp4 files are on disk but not in sessions.json, synthesize entries
    recorded_files = {s["filename"] for s in valid_sessions}
    for f in sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.name not in recorded_files:
            clean_q = f.name.replace(".mp4", "").replace("_", " ")
            clean_q = clean_q[16:] if len(clean_q) > 16 else clean_q
            entry = {
                "id": f.stem,
                "question": clean_q,
                "provider": "groq",
                "steps": [],
                "filename": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d %b %Y, %I:%M %p"),
            }
            valid_sessions.append(entry)

    return jsonify(valid_sessions)


@app.route("/api/session/<session_id>")
def api_session(session_id):
    """Retrieves full details of a specific chat session."""
    saved = _load_history()
    for s in saved:
        if s.get("id") == session_id or s.get("filename") == session_id or s.get("filename") == f"{session_id}.mp4":
            return jsonify(s)

    # Fallback to checking disk
    f = OUTPUT_DIR / f"{session_id}.mp4"
    if not f.exists():
        f = OUTPUT_DIR / session_id
    if f.exists():
        clean_q = f.stem[16:].replace("_", " ") if len(f.stem) > 16 else f.stem.replace("_", " ")
        return jsonify({
            "id": f.stem,
            "question": clean_q,
            "provider": "groq",
            "steps": [],
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d %b %Y, %I:%M %p"),
        })

    return jsonify({"error": "Session not found"}), 404


@app.route("/api/videos")
def api_videos():
    return api_history()


@app.route("/video/<filename>")
def serve_video(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return "Video not found", 404
    return send_file(str(path), mimetype="video/mp4")


@app.route("/api/providers")
def api_providers():
    from ai_provider import list_providers
    return jsonify(list_providers())


# ── Entry Point ───────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  VisuAIze Web App - Starting...")
    print("=" * 55)
    print(f"  AI Provider : {os.getenv('AI_PROVIDER', 'groq').upper()}")
    print(f"  Output Dir  : {OUTPUT_DIR.resolve()}")
    print(f"  URL         : http://127.0.0.1:5000")
    print("=" * 55)
    print("  Opening browser automatically...")
    print("  Press Ctrl+C to stop the server.\n")

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, host="127.0.0.1", port=5000, threaded=True)
