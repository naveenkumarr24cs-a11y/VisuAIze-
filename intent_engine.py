"""
VisuAIze Intent Classification, Context Management and Orchestration Engine
===========================================================================
Architecture:
  User Input -> Intent Classification -> Context Management -> Structured Output -> Orchestration

4 Core Features:
  1. Intent Classification  - 6 intent types with local heuristics + Groq/Gemini LLM
  2. Context Management     - Remembers last 5 sessions, resolves follow-up references
  3. Structured Output      - Full JSON spec: subject, style, tone, scene, platform, etc.
  4. Orchestration Ready    - spec["intent"] drives server.py orchestration layer
"""

import json
import os
import re
from typing import Dict, Any, List, Optional


INTENT_SYSTEM_PROMPT = """You are the Lead Intelligence Orchestrator for VisuAIze, an AI cinematic step-by-step video tutorial platform.

Analyze the user input and conversation history, then return ONLY a valid JSON object (no markdown, no extra text).

Classify into EXACTLY ONE intent:
1. "NEW_VIDEO": User wants to create a new step-by-step visual video tutorial on a clear topic.
2. "MODIFY_VIDEO": User wants to modify an existing video (e.g. "make it shorter", "change background", "more realistic").
3. "REGENERATE_VIDEO": User wants to re-render the current video with fresh visuals.
4. "CLARIFY_REQUIRED": Topic is too broad/ambiguous (e.g. "cars", "make a video"). Ask a focused clarification question.
5. "GENERAL_CONVERSATION": User is chatting, greeting, or asking a non-video question. Answer helpfully.
6. "REJECT_UNREALISTIC": Pure gibberish, random letters with no meaning. Reject politely with suggestions.

Return ONLY this JSON structure:
{
  "intent": "NEW_VIDEO|MODIFY_VIDEO|REGENERATE_VIDEO|CLARIFY_REQUIRED|GENERAL_CONVERSATION|REJECT_UNREALISTIC",
  "subject": "Clean specific title of the video tutorial",
  "style": "Visual style (e.g. photorealistic cinematic 3D, futuristic sci-fi, documentary)",
  "tone": "Narration tone (e.g. clear and educational, fast-paced, calm professional)",
  "scene": "Environment setting (e.g. inside the human body, space station, chemistry lab)",
  "platform": "Target platform (e.g. YouTube educational, social media short)",
  "complexity": "STUDENT",
  "num_steps": 5,
  "target_duration_sec": 60,
  "modifications": [],
  "clarification_question": "",
  "conversation_response": "",
  "suggestions": []
}

CRITICAL RULES:
- "hi", "hello", "hey", "hii" MUST be GENERAL_CONVERSATION with a friendly helpful response
- "make it shorter", "change background", "more realistic" MUST be MODIFY_VIDEO
- Only reject truly random gibberish with no meaning
- Single-word topics like "photosynthesis", "gravity" = NEW_VIDEO (they are clear enough)
"""


def normalize_complexity(level_raw: Any) -> str:
    if not level_raw:
        return "STUDENT"
    s = str(level_raw).upper().strip()
    if any(k in s for k in ["EL5", "ELI5", "5YO", "CHILD", "KID", "SIMPLE", "BEGINNER"]):
        return "EL5"
    if any(k in s for k in ["EXPERT", "ADVANCED", "PROFESSIONAL", "PRO", "TECHNICAL", "MASTER"]):
        return "EXPERT"
    return "STUDENT"


def _clean_json_obj(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _build_context_summary(history: Optional[List[Dict[str, Any]]]) -> str:
    if not history:
        return ""
    lines = ["CONVERSATION HISTORY (most recent first):"]
    for h in history[:5]:
        q = h.get("question") or h.get("subject", "")
        typ = h.get("type", "video")
        fn = h.get("filename", "")
        if q:
            entry = f"  - [{typ.upper()}] '{q}'"
            if fn:
                entry += f" (video: {fn})"
            lines.append(entry)
    return "\n".join(lines) + "\n\n"


def _build_user_prompt(question: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    context = _build_context_summary(history)
    comp = normalize_complexity(question)
    return (
        f"{context}"
        f"CURRENT USER MESSAGE: \"{question}\"\n"
        f"COMPLEXITY HINT: {comp}\n\n"
        f"Return ONLY the JSON specification. Greetings are GENERAL_CONVERSATION."
    )


def _default_spec(question: str, intent: str = "NEW_VIDEO", chat_msg: str = "") -> Dict[str, Any]:
    return {
        "intent": intent,
        "subject": question if intent not in ("GENERAL_CONVERSATION", "REJECT_UNREALISTIC") else "",
        "style": "photorealistic cinematic 3D",
        "tone": "clear and educational",
        "scene": "dynamic educational environment",
        "platform": "YouTube educational",
        "complexity": normalize_complexity(question),
        "num_steps": 5,
        "target_duration_sec": 60,
        "modifications": [],
        "clarification_question": "",
        "conversation_response": chat_msg,
        "suggestions": []
    }


def _local_heuristics_classifier(
    question: str,
    history: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Fast deterministic local classification before calling LLM."""
    q = question.strip()
    q_lower = q.lower()
    words = q.split()

    # Greetings
    greetings = ["hi", "hello", "hey", "hii", "helo", "hiya", "howdy", "sup", "yo",
                 "good morning", "good evening", "good afternoon", "namaste", "greetings"]
    q_stripped = q_lower.rstrip("!").rstrip(".").strip()
    if q_stripped in greetings or q_lower in greetings:
        return _default_spec(q, "GENERAL_CONVERSATION",
            "Hello! I am **VisuAIze** - your AI cinematic video tutorial creator!\n\n"
            "I turn any topic or question into a **photorealistic, cinematic step-by-step video** "
            "with professional narration, Ken Burns camera motion, and smooth transitions.\n\n"
            "**Try asking:**\n"
            "- *How does the human heart pump blood?*\n"
            "- *Explain how a car engine works*\n"
            "- *How to tie a tie knot*\n"
            "- *What is machine learning?*\n\n"
            "What topic would you like to visualize today?")

    # Too short
    if len(q) < 3:
        return _default_spec(q, "REJECT_UNREALISTIC")

    # Pure gibberish
    if len(words) >= 2 and all(len(w) <= 2 for w in words if w.isalpha()):
        return {**_default_spec(q, "REJECT_UNREALISTIC"),
                "suggestions": ["How does the human heart work?",
                                "How to make scrambled eggs",
                                "How to tie a tie knot",
                                "Explain machine learning"]}

    # Platform questions about VisuAIze itself
    platform_q = ["what is visuaize", "how does visuaize work", "what can you do",
                  "who made you", "what models", "how do you work", "what are you"]
    if any(pt in q_lower for pt in platform_q):
        return _default_spec(q, "GENERAL_CONVERSATION",
            "**VisuAIze** is an AI cinematic tutorial platform powered by:\n\n"
            "- **AI Script Engine**: Groq Llama 3.3 / Gemini 2.0 Flash\n"
            "- **Visual Engine**: HuggingFace SD3 Medium + Pollinations Flux\n"
            "- **Voice Engine**: gTTS with audio-sync narration\n"
            "- **Video Engine**: Ken Burns motion + cinematic transitions + H.264\n\n"
            "Just describe any topic and I will create a cinematic tutorial video!")

    # Modification follow-up (requires history context)
    mod_triggers = ["make it", "change the", "add a step", "remove step", "faster", "slower",
                    "shorter", "longer", "darker", "brighter", "re-render", "regenerate",
                    "more realistic", "different style", "change background", "more cinematic",
                    "make the video", "redo it", "redo the", "change it", "try again"]
    if history and any(trig in q_lower for trig in mod_triggers):
        last_session = next(
            (s for s in history if s.get("filename") and s.get("type") != "chat"),
            history[0] if history else {}
        )
        last_subject = last_session.get("question") or last_session.get("subject", "Tutorial Video")
        return {
            "intent": "MODIFY_VIDEO",
            "subject": last_subject,
            "style": "photorealistic cinematic 3D",
            "tone": "clear and educational",
            "scene": "dynamic educational environment",
            "platform": "YouTube educational",
            "complexity": normalize_complexity(question),
            "num_steps": 5,
            "target_duration_sec": 60,
            "modifications": [q],
            "clarification_question": "",
            "conversation_response": "",
            "suggestions": []
        }

    return None  # Defer to LLM


def _classify_with_groq(question: str, history: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """Feature 1: Intent Classification via Groq Llama 3.3 70B (fastest)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = _build_user_prompt(question, history)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        return _clean_json_obj(resp.choices[0].message.content)
    except Exception as e:
        print(f"[IntentEngine/Groq] {e}")
        return None


def _classify_with_gemini(question: str, history: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """Fallback: Intent Classification via Google Gemini 2.0 Flash."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        prompt = _build_user_prompt(question, history)
        full = f"{INTENT_SYSTEM_PROMPT}\n\n{prompt}"
        resp = model.generate_content(full)
        return _clean_json_obj(resp.text)
    except Exception as e:
        print(f"[IntentEngine/Gemini] {e}")
        return None


def _apply_spec_defaults(spec: Dict[str, Any], question: str):
    """Feature 3: Validate and apply defaults to structured output."""
    spec.setdefault("intent", "NEW_VIDEO")
    spec.setdefault("subject", question)
    spec.setdefault("style", "photorealistic cinematic 3D")
    spec.setdefault("tone", "clear and educational")
    spec.setdefault("scene", "dynamic educational environment")
    spec.setdefault("platform", "YouTube educational")
    spec.setdefault("modifications", [])
    spec.setdefault("clarification_question", "")
    spec.setdefault("conversation_response", "")
    spec.setdefault("suggestions", [])
    spec["complexity"] = normalize_complexity(spec.get("complexity") or question)
    if spec.get("intent") in ("NEW_VIDEO", "MODIFY_VIDEO", "REGENERATE_VIDEO"):
        try:
            val = int(spec.get("num_steps") or 5)
            spec["num_steps"] = min(max(val, 4), 6)
        except (ValueError, TypeError):
            spec["num_steps"] = 5
        spec.setdefault("target_duration_sec", 60)


def _resolve_modification_context(spec: Dict[str, Any], question: str, history: List[Dict[str, Any]]):
    """Feature 2: Context Management - resolve follow-up references to previous sessions."""
    last_video = next(
        (s for s in history if s.get("filename") and s.get("type") != "chat"),
        history[0] if history else None
    )
    if not last_video:
        return
    last_subject = last_video.get("question") or last_video.get("subject", "")
    if not spec.get("subject") or spec.get("subject") == question:
        spec["subject"] = last_subject
    print(f"[Context] Modification resolved against: '{spec.get('subject')}'")


def analyze_intent_and_context(
    question: str,
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main entry point - implements all 4 architecture features:
      1. Intent Classification  -> classify into 6 intents
      2. Context Management     -> resolve follow-up against history
      3. Structured Output      -> return full JSON video spec
      4. Orchestration Ready    -> spec["intent"] drives server.py
    """
    # Feature 1a: Local heuristics (instant, zero API cost)
    local_result = _local_heuristics_classifier(question, history)
    if local_result is not None:
        _apply_spec_defaults(local_result, question)
        return local_result

    # Feature 1b: LLM classification (Groq first, Gemini fallback)
    spec = _classify_with_groq(question, history)
    if spec is None:
        spec = _classify_with_gemini(question, history)
    if spec is None:
        print("[IntentEngine] All classifiers failed - defaulting to NEW_VIDEO")
        return _default_spec(question, "NEW_VIDEO")

    # Feature 3: Validate structured output
    _apply_spec_defaults(spec, question)

    # Feature 2: Context resolution for modification intents
    if spec.get("intent") in ("MODIFY_VIDEO", "REGENERATE_VIDEO") and history:
        _resolve_modification_context(spec, question, history)

    return spec
