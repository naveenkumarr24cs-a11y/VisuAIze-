"""
VisuAIze - Web Application Server
A beautiful Flask web app that provides a browser UI for generating
step-by-step instructional videos. Opens browser automatically on launch.
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

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# Active job progress queues: job_id → Queue of SSE events
_job_queues: dict[str, queue.Queue] = {}
_job_status: dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _run_pipeline(job_id: str, question: str, provider: str, image_path: str | None):
    """Runs the full VisuAIze pipeline in a background thread, pushing SSE progress."""
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

        # Phase 1 – Generate steps
        push(1, 4, f"Generating steps with {provider.title()} AI...", "Analyzing your question")
        from ai_provider import generate_steps
        steps = generate_steps(question, image_path)
        push(1, 4, f"Got {len(steps)} steps!", ", ".join(s["title"] for s in steps[:3]) + "...")

        # Phase 2 – Generate images
        push(2, 4, "Building presentation slides...", f"Locally generating {len(steps)} high-quality slides")
        from image_generator import generate_all_images
        image_paths = generate_all_images(steps, str(tmp_images))
        push(2, 4, "All images ready!", f"{len(image_paths)} images generated")

        # Phase 3 – Generate voice
        push(3, 4, "Generating voice narrations...", f"Creating {len(steps) + 2} audio clips")
        from voice_generator import generate_all_voices
        audio_data = generate_all_voices(steps, str(tmp_audio))
        push(3, 4, "Voice narrations done!", "All audio clips created")

        # Phase 4 – Assemble video
        push(4, 4, "Assembling final video...", "Stitching images, audio & overlays with FFmpeg")
        from video_assembler import assemble_video
        assemble_video(steps=steps, image_paths=image_paths,
                       audio_data=audio_data, output_path=output_path, topic=question)

        # Cleanup temp
        shutil.rmtree(TEMP_DIR / session, ignore_errors=True)

        file_size = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
        video_filename = Path(output_path).name
        _job_status[job_id] = {"status": "done", "filename": video_filename,
                                "size_mb": file_size, "steps": len(steps)}
        q.put({"type": "done", "filename": video_filename,
               "size_mb": file_size, "steps": len(steps)})

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
    """Server-Sent Events stream for real-time progress updates."""
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


@app.route("/api/videos")
def api_videos():
    videos = []
    for f in sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        videos.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d %b %Y, %I:%M %p"),
        })
    return jsonify(videos)


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
