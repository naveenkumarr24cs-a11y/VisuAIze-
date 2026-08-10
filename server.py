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
from typing import Any

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file
import firebase_manager

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
_history_lock = threading.Lock()   # protects sessions.json from concurrent writes


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
    with _history_lock:   # thread-safe write
        sessions = _load_history()
        # Deduplicate by `id` first, then by `filename` to prevent overwrites
        new_id = session_data.get("id")
        new_fn = session_data.get("filename")
        sessions = [
            s for s in sessions
            if not (
                (new_id and s.get("id") == new_id) or
                (new_fn and new_fn != "" and s.get("filename") == new_fn)
            )
        ]
        sessions.insert(0, session_data)
        _save_history(sessions[:100])   # keep last 100 sessions

    # Sync to Firebase asynchronously (no impact on response time)
    firebase_manager.save_chat_session_async(session_data)


def _schedule_cleanup(job_id: str, delay: float = 1800.0):
    """Remove finished job queues after `delay` seconds to prevent memory leak."""
    def _do_cleanup():
        time.sleep(delay)
        _job_queues.pop(job_id, None)
        _job_status.pop(job_id, None)
    threading.Thread(target=_do_cleanup, daemon=True).start()


# ── Pipeline Runner ──────────────────────────────────────────────────────────

def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _run_pipeline(job_id: str, question_or_spec: Any, provider: str, image_path: str | None):
    q = _job_queues[job_id]

    def push(phase: int, total: int, message: str, detail: str = ""):
        pct = int((phase / total) * 100)
        q.put({"type": "progress", "phase": phase, "total": total,
               "pct": pct, "message": message, "detail": detail})

    try:
        original_provider = os.environ.get("AI_PROVIDER", "groq")
        os.environ["AI_PROVIDER"] = provider

        if isinstance(question_or_spec, dict):
            question = question_or_spec.get("subject", "Tutorial Video")
            spec = question_or_spec
        else:
            question = str(question_or_spec)
            spec = {"subject": question}

        # Extract NotebookLM intelligence parameters
        visual_style = spec.get("visual_style", "classic") or "classic"
        dual_voice   = bool(spec.get("dual_voice", True))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c for c in question[:30] if c.isalnum() or c in " _-").strip().replace(" ", "_")
        session = f"{timestamp}_{safe}"

        tmp_images = TEMP_DIR / session / "images"
        tmp_audio  = TEMP_DIR / session / "audio"
        tmp_images.mkdir(parents=True, exist_ok=True)
        tmp_audio.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / f"{session}.mp4")

        # Phase 1 – NotebookLM P→A→S AI Scripting
        push(1, 4, f"🧠 Generating P→A→S script with {provider.title()} AI...",
             "Problem → Analogy → Solution pedagogical structure")
        try:
            from pedagogy_engine import generate_pedagogical_script, pedagogical_to_steps
            pas_script = generate_pedagogical_script(
                topic=question,
                visual_style=visual_style,
                complexity=spec.get("complexity", "STUDENT")
            )
            steps = pedagogical_to_steps(pas_script)
            print(f"[Pedagogy] P→A→S script: {len(steps)} steps generated")
        except Exception as e:
            print(f"[Pedagogy] Fallback to legacy generator: {e}")
            from ai_provider import generate_steps
            steps = generate_steps(spec, image_path)

        if not steps:
            raise ValueError("The AI model was unable to generate steps for this topic. Please try rephrasing your request.")

        push(1, 4, f"✅ Script ready ({len(steps)} steps)!",
             ", ".join(s["title"] for s in steps[:3]) + "...")

        # Phase 2 – AI Visual Slides (Parallel)
        push(2, 4, f"🎨 Generating {visual_style} style visual slides...",
             f"Fetching AI images for {len(steps)} steps in parallel")
        from image_generator import generate_all_images
        image_paths = generate_all_images(steps, str(tmp_images), topic=question,
                                          visual_style=visual_style)
        push(2, 4, "✅ All visual slides ready!",
             f"{len(image_paths)} {visual_style} slides generated")

        # Phase 3 – Dual-Voice Narrations
        push(3, 4, "🎙️ Recording dual-speaker narrations...",
             f"Teacher + Student voices for {len(steps) + 2} clips" if dual_voice
             else f"Synthesising {len(steps) + 2} audio clips")
        from voice_generator import generate_all_voices
        audio_data = generate_all_voices(steps, str(tmp_audio), dual_voice=dual_voice)
        push(3, 4, "✅ Voice narrations ready!", "All audio clips created")

        # Phase 4 – Animated Video Assembly
        push(4, 4, "🎬 Assembling animated tutorial video...",
             f"Ken Burns · {visual_style} style · crossfade · H.264")
        from video_assembler import assemble_video
        assemble_video(
            steps=steps, image_paths=image_paths,
            audio_data=audio_data, output_path=output_path,
            topic=question, job_id=job_id,
            visual_style=visual_style
        )

        os.environ["AI_PROVIDER"] = original_provider
        shutil.rmtree(TEMP_DIR / session, ignore_errors=True)

        file_size = round(Path(output_path).stat().st_size / (1024 * 1024), 1)
        video_filename = Path(output_path).name

        session_record = {
            "id": session,
            "question": question,
            "provider": provider,
            "steps": steps,
            "filename": video_filename,
            "size_mb": file_size,
            "visual_style": visual_style,
            "dual_voice": dual_voice,
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
        tb  = traceback.format_exc()
        _job_status[job_id] = {"status": "error", "error": err}
        q.put({"type": "error", "error": err, "traceback": tb})

    finally:
        _schedule_cleanup(job_id, delay=1800.0)




# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           current_provider=os.getenv("AI_PROVIDER", "groq"))


@app.route("/api/validate", methods=["POST"])
def api_validate():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or request.form.get("question", "")).strip()
    if not question:
        return jsonify({"valid": False, "reason": "Please enter a topic or question.", "refined_topic": ""})

    from intent_engine import analyze_intent_and_context
    spec = analyze_intent_and_context(question, _load_history())
    return jsonify({
        "valid": spec["intent"] in ("NEW_VIDEO", "MODIFY_VIDEO", "REGENERATE_VIDEO"),
        "reason": spec.get("clarification_question") or spec.get("conversation_response") or "",
        "refined_topic": spec.get("subject", question),
        "intent": spec["intent"]
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    question    = request.form.get("question", "").strip()
    provider    = request.form.get("provider", os.getenv("AI_PROVIDER", "groq")).strip()
    image_file  = request.files.get("image")
    style       = request.form.get("style", "classic").strip() or "classic"
    dual_voice  = request.form.get("dual_voice", "true").strip().lower() in ("true", "1", "yes")

    if not question:
        return jsonify({"action": "refusal", "error": "Please enter a topic or question."}), 422

    # ── 1. Intent Classification & Context Management ──────────────────────
    from intent_engine import analyze_intent_and_context
    history = _load_history()

    # Build conversation context: include last 5 sessions for follow-up understanding
    context_history = history[:5] if history else []

    spec = analyze_intent_and_context(question, context_history)

    intent = spec.get("intent", "NEW_VIDEO")
    print(f"[Orchestration] Intent: {intent} | Subject: '{spec.get('subject')}'")

    # ── 2. Context Resolution for Modification Requests ────────────────────
    # If the user says "make it shorter" or "change background", resolve against last session
    if intent in ("MODIFY_VIDEO", "REGENERATE_VIDEO") and history:
        last_session = history[0]
        # Inherit subject from last video session if not set
        if not spec.get("subject") or spec.get("subject") == question:
            spec["subject"] = last_session.get("question") or last_session.get("subject") or question
        # Inherit steps from last session if not regenerating
        if intent == "MODIFY_VIDEO" and last_session.get("steps"):
            spec["_previous_steps"] = last_session["steps"]
            spec["_previous_session_id"] = last_session.get("id")
        print(f"[Context] Resolved against last session: '{spec.get('subject')}'")

    # Inject visual style + dual voice into spec
    spec["visual_style"] = style
    spec["dual_voice"] = dual_voice
    print(f"[Style] Visual style: {style} | Dual-Voice: {dual_voice}")

    # ── 2. Orchestration Action Branching ──────────────────────────────────
    if intent == "GENERAL_CONVERSATION":
        session_id = f"chat_{int(time.time() * 1000)}"
        chat_msg = spec.get("conversation_response", "Hello! How can I assist you today? Do you want to create a new video tutorial or discuss something?")
        session_entry = {
            "id": session_id,
            "question": question,
            "subject": question,
            "created": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "timestamp": datetime.now().isoformat(),
            "type": "chat",
            "messages": [
                {"sender": "user", "text": question},
                {"sender": "assistant", "text": chat_msg}
            ]
        }
        _add_session(session_entry)
        return jsonify({
            "action": "chat",
            "session_id": session_id,
            "message": chat_msg
        }), 200

    if intent == "CLARIFY_REQUIRED":
        return jsonify({
            "action": "clarify",
            "question": spec.get("clarification_question", "Could you clarify what specific topic you'd like to learn?"),
            "suggestions": spec.get("suggestions", [])
        }), 200

    if intent == "REJECT_UNREALISTIC":
        return jsonify({
            "action": "refusal",
            "error": "That input is not a valid tutorial topic.",
            "suggestions": spec.get("suggestions", [])
        }), 422

    # Intent: NEW_VIDEO / MODIFY_VIDEO / REGENERATE_VIDEO -> Trigger Video Pipeline
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
        args=(job_id, spec, provider, image_path),
        daemon=True,
    )
    thread.start()

    return jsonify({"action": "video", "job_id": job_id, "style": style})




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


def _sync_firebase_history_bg():
    """Fetch Firebase sessions in background thread and update sessions.json without blocking HTTP requests."""
    def _worker():
        try:
            fb_sessions = firebase_manager.fetch_chat_history()
            if not fb_sessions:
                return
            with _history_lock:
                saved = _load_history()
                recorded_ids = {s.get("id") or s.get("filename") for s in saved if s.get("id") or s.get("filename")}
                added = False
                for fs in fb_sessions:
                    fs_id = fs.get("id") or fs.get("filename")
                    if fs_id and fs_id not in recorded_ids:
                        saved.append(fs)
                        recorded_ids.add(fs_id)
                        added = True
                if added:
                    _save_history(saved[:100])
                    print(f"🔥 [Firebase] Synced {len(saved)} cloud sessions into local sessions.json!")
        except Exception as e:
            print(f"⚠️ [Firebase] Background sync notice: {e}")

    threading.Thread(target=_worker, daemon=True).start()


@app.route("/api/history")
def api_history():
    """Returns all past chat/video sessions instantly (0ms) from local cache and syncs Firebase in background."""
    saved = _load_history()

    # Trigger background sync from Firebase
    _sync_firebase_history_bg()

    # Include all saved sessions (chats and videos)
    recorded_ids = set()
    valid_sessions = []
    for s in saved:
        s_id = s.get("id") or s.get("filename")
        if s_id and s_id not in recorded_ids:
            valid_sessions.append(s)
            recorded_ids.add(s_id)

    # If some mp4 files are on disk but not in sessions, synthesize entries
    recorded_files = {s.get("filename") for s in valid_sessions if s.get("filename")}
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


@app.route("/api/history/<session_id>", methods=["DELETE"])
@app.route("/api/history/delete", methods=["POST"])
def api_delete_history(session_id=None):
    """Deletes a chat session from local storage and Firebase Cloud database."""
    if not session_id and request.is_json:
        session_id = request.json.get("id") or request.json.get("session_id") or request.json.get("filename")
    if not session_id:
        session_id = request.args.get("id")

    if not session_id:
        return jsonify({"error": "Missing session ID"}), 400

    clean_id = session_id.replace(".mp4", "")
    filename = f"{clean_id}.mp4"

    # 1. Remove from local sessions.json
    with _history_lock:
        saved = _load_history()
        updated = [s for s in saved if s.get("id") != clean_id and s.get("filename") != filename and s.get("id") != session_id]
        _save_history(updated)

    # 2. Delete from Firebase
    firebase_manager.delete_chat_session_async(clean_id)
    firebase_manager.delete_chat_session_async(filename)

    # 3. Delete local mp4 file if present
    target_mp4 = OUTPUT_DIR / filename
    if target_mp4.exists():
        try:
            target_mp4.unlink()
            print(f"🗑️ [History] Deleted video file: {target_mp4}")
        except Exception as e:
            print(f"⚠️ [History] File delete warning: {e}")

    return jsonify({"success": True, "deleted_id": session_id})


@app.route("/api/session/<session_id>")
def api_session(session_id):
    """Retrieves full details of a specific chat session."""
    saved = _load_history()
    for s in saved:
        if s.get("id") == session_id or s.get("filename") == session_id or s.get("filename") == f"{session_id}.mp4":
            return jsonify(s)

    # Check Firebase
    try:
        fb_sessions = firebase_manager.fetch_chat_history()
        for s in fb_sessions:
            if s.get("id") == session_id or s.get("filename") == session_id:
                return jsonify(s)
    except Exception:
        pass

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



@app.route("/api/firebase/status")
def api_firebase_status():
    """Returns Firebase Cloud Sync connection status."""
    return jsonify(firebase_manager.get_firebase_status())


@app.route("/api/firebase/sync", methods=["POST"])
def api_firebase_sync():
    """Manually trigger sync of all local sessions to Firebase Cloud."""
    sessions = _load_history()
    synced_count = 0
    for s in sessions:
        if firebase_manager.save_chat_session(s):
            synced_count += 1
    return jsonify({
        "status": "SUCCESS",
        "synced_count": synced_count,
        "total_count": len(sessions),
        "firebase": firebase_manager.get_firebase_status()
    })


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
