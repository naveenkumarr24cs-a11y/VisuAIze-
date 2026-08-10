"""
VisuAIze - Firebase Sync Manager
================================
Syncs chat session history, prompts, step narrations, and video metadata to Firebase Firestore / Realtime DB.
Supports:
  1. firebase-admin Firestore (using service account credentials or project ID)
  2. Firebase Realtime DB / REST API (using FIREBASE_DATABASE_URL)
  3. Seamless async background thread syncing (0ms impact on video creation speed)
"""

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Global Firebase State ───────────────────────────────────────────────────
_db_client = None
_firebase_initialized = False
_firebase_status = {
    "status": "LOCAL_ONLY",
    "message": "Local backup active. Add FIREBASE_SERVICE_ACCOUNT or FIREBASE_DATABASE_URL to enable Cloud Sync.",
    "mode": None
}


def init_firebase() -> bool:
    """Initialize Firebase Admin SDK or REST endpoint."""
    global _db_client, _firebase_initialized, _firebase_status

    if _firebase_initialized:
        return _db_client is not None

    # Check for Service Account JSON path in env or current dir
    creds_path = os.getenv("FIREBASE_SERVICE_ACCOUNT") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        local_service_account = Path("firebase_service_account.json")
        if local_service_account.exists():
            creds_path = str(local_service_account.resolve())

    db_url = os.getenv("FIREBASE_DATABASE_URL")
    project_id = os.getenv("FIREBASE_PROJECT_ID")

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if creds_path and Path(creds_path).exists():
            print(f"🔥 [Firebase] Initializing with Service Account: {creds_path}")
            cred = credentials.Certificate(creds_path)
            options = {"databaseURL": db_url} if db_url else {}
            if not firebase_admin._apps:
                app = firebase_admin.initialize_app(cred, options)
            _db_client = firestore.client()
            _firebase_initialized = True
            _firebase_status = {
                "status": "CONNECTED",
                "message": "Firebase Firestore Cloud Sync active!",
                "mode": "FIRESTORE_ADMIN"
            }
            return True
        elif project_id:
            print(f"🔥 [Firebase] Initializing with Project ID: {project_id}")
            if not firebase_admin._apps:
                app = firebase_admin.initialize_app(options={"projectId": project_id})
            _db_client = firestore.client()
            _firebase_initialized = True
            _firebase_status = {
                "status": "CONNECTED",
                "message": f"Firebase Firestore active (Project: {project_id})",
                "mode": "FIRESTORE_PROJECT"
            }
            return True
    except Exception as e:
        print(f"⚠️ [Firebase] Admin SDK init notice: {e}")

    # Fallback check for REST Realtime DB if URL provided
    if db_url:
        _firebase_initialized = True
        _firebase_status = {
            "status": "CONNECTED",
            "message": "Firebase Realtime DB REST sync active!",
            "mode": "REST_DB"
        }
        return True

    _firebase_initialized = True
    print("ℹ️ [Firebase] Local mode active (No Firebase credentials configured yet).")
    return False


def save_chat_session_async(session_data: Dict[str, Any]):
    """Sync a chat session to Firebase asynchronously in a background thread."""
    def _worker():
        try:
            save_chat_session(session_data)
        except Exception as e:
            print(f"⚠️ [Firebase] Async save warning: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def save_chat_session(session_data: Dict[str, Any]) -> bool:
    """Save/update chat session in Firebase collection 'chat_sessions'."""
    init_firebase()
    if not session_data or not isinstance(session_data, dict):
        return False

    session_id = session_data.get("id") or session_data.get("filename") or session_data.get("session_id")
    if not session_id:
        return False

    # Store full session_data payload dictionary cleanly
    payload = dict(session_data)
    payload["id"] = session_id
    payload["synced_at"] = firestore_timestamp_str()

    # 1. Save via Firestore SDK
    if _db_client is not None:
        try:
            doc_ref = _db_client.collection("chat_sessions").document(session_id)
            doc_ref.set(payload, merge=True)
            print(f"🔥 [Firebase] Successfully saved session '{session_id}' to Firestore!")
            return True
        except Exception as e:
            print(f"⚠️ [Firebase] Firestore save error: {e}")

    # 2. Save via Realtime DB REST API if configured
    db_url = os.getenv("FIREBASE_DATABASE_URL")
    if db_url:
        try:
            import requests
            url = f"{db_url.rstrip('/')}/chat_sessions/{session_id}.json"
            res = requests.put(url, json=payload, timeout=5.0)
            if res.status_code in (200, 201):
                print(f"🔥 [Firebase] Saved session '{session_id}' via Realtime DB REST!")
                return True
        except Exception as e:
            print(f"⚠️ [Firebase] REST DB save error: {e}")

    return False


def fetch_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch chat history sessions from Firebase Firestore, sorted by timestamp descending."""
    init_firebase()
    if _db_client is not None:
        try:
            docs = (
                _db_client.collection("chat_sessions")
                .limit(limit)
                .stream()
            )
            sessions = [d.to_dict() for d in docs]
            if sessions:
                sessions.sort(key=lambda s: s.get("timestamp") or s.get("created") or "", reverse=True)
                return sessions
        except Exception as e:
            print(f"⚠️ [Firebase] Firestore fetch error: {e}")

    db_url = os.getenv("FIREBASE_DATABASE_URL")
    if db_url:
        try:
            import requests
            url = f"{db_url.rstrip('/')}/chat_sessions.json?shallow=false"
            res = requests.get(url, timeout=5.0)
            if res.status_code == 200 and res.json():
                data = res.json()
                sessions = list(data.values()) if isinstance(data, dict) else []
                sessions.sort(key=lambda s: s.get("timestamp") or s.get("created") or "", reverse=True)
                return sessions
        except Exception as e:
            print(f"⚠️ [Firebase] REST fetch error: {e}")

    return []


def delete_chat_session(session_id: str) -> bool:
    """Delete a chat session from Firebase Firestore / Realtime DB."""
    init_firebase()
    if not session_id:
        return False

    success = False

    # 1. Delete from Firestore SDK
    if _db_client is not None:
        try:
            doc_ref = _db_client.collection("chat_sessions").document(session_id)
            doc_ref.delete()
            print(f"🔥 [Firebase] Deleted session '{session_id}' from Firestore.")
            success = True
        except Exception as e:
            print(f"⚠️ [Firebase] Firestore delete error: {e}")

    # 2. Delete from Realtime DB REST API if configured
    db_url = os.getenv("FIREBASE_DATABASE_URL")
    if db_url:
        try:
            import requests
            url = f"{db_url.rstrip('/')}/chat_sessions/{session_id}.json"
            res = requests.delete(url, timeout=5.0)
            if res.status_code in (200, 204):
                print(f"🔥 [Firebase] Deleted session '{session_id}' from Realtime DB REST.")
                success = True
        except Exception as e:
            print(f"⚠️ [Firebase] REST DB delete error: {e}")

    return success


def delete_chat_session_async(session_id: str):
    """Delete a chat session from Firebase asynchronously."""
    def _worker():
        try:
            delete_chat_session(session_id)
        except Exception as e:
            print(f"⚠️ [Firebase] Async delete warning: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def get_firebase_status() -> Dict[str, Any]:
    """Get current Firebase connection status."""
    init_firebase()
    return _firebase_status


def firestore_timestamp_str() -> str:
    from datetime import datetime
    return datetime.now().isoformat()

