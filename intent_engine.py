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
1. "NEW_VIDEO": User wants to create a video tutorial, learn something, solve a problem, or explore ANY topic/concept/subject (e.g. "how to study", "Java", "Python", "quantum physics", "how does a turbocharger work", "calculus", "machine learning", "history of Rome", "origami", "how to tie a knot").
   CRITICAL RULE: Even if the user's input is short or broad (like "Java" or "how to study" or "space"), ALWAYS classify as "NEW_VIDEO". Automatically synthesize a clean, descriptive, and comprehensive tutorial title for "subject" (e.g. "how to study" -> "Effective Study Techniques & Cognitive Learning Strategies"; "Java" -> "Java Programming Fundamentals & Core OOP Concepts"). DO NOT ask for clarification or refuse.
2. "MODIFY_VIDEO": User wants to modify the previous video (e.g. "make it shorter", "change background", "more realistic", "different style").
3. "REGENERATE_VIDEO": User wants to re-render the current video with fresh visuals.
4. "GENERAL_CONVERSATION": User is chatting, greeting ("hi", "hello"), asking what VisuAIze can do, or having a conversational exchange. Provide a rich, highly intelligent conversational response like ChatGPT / Gemini in "conversation_response".
5. "CLARIFY_REQUIRED": ONLY for completely empty, single-punctuation, or 1-letter inputs (e.g. "?", "...", "x"). For any real topic, use NEW_VIDEO.
6. "REJECT_UNREALISTIC": ONLY for pure random keyboard mash (e.g. "asdfghjkl", "12837198273").

Return ONLY this JSON structure:
{
  "intent": "NEW_VIDEO|MODIFY_VIDEO|REGENERATE_VIDEO|GENERAL_CONVERSATION|CLARIFY_REQUIRED|REJECT_UNREALISTIC",
  "subject": "Clean specific comprehensive title of the video tutorial",
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
- ANY instructional, educational, problem-solving, or subject prompt MUST be NEW_VIDEO
- Never return empty or generic suggestions; if suggestions are needed, make them directly relevant to the user's topic
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

    # Short topic acronyms that should immediately be NEW_VIDEO
    short_acronyms = {
        "ai": "Artificial Intelligence Fundamentals & How It Works",
        "ml": "Machine Learning Core Concepts & Algorithms",
        "dl": "Deep Learning & Neural Network Architecture",
        "c": "C Programming Language Fundamentals",
        "c++": "C++ Object-Oriented Programming & STL",
        "go": "Golang Programming Language Essentials",
        "js": "JavaScript Essentials & Modern Web Concepts",
        "ts": "TypeScript Fundamentals & Static Typing",
        "py": "Python Programming for Beginners & Core Syntax",
        "sql": "SQL Database Queries, Joins & Optimization",
        "git": "Git Version Control & Branching Strategies",
        "vr": "Virtual Reality (VR) Technology & Headsets",
        "ar": "Augmented Reality (AR) Principles & Applications",
        "ui": "User Interface (UI) Design Principles & Layouts",
        "ux": "User Experience (UX) Research & User Journey Design",
        "3d": "3D Modeling, Rendering & Spatial Graphics",
        "os": "Operating Systems: Kernel, Memory & Process Scheduling",
        "db": "Database Systems: Relational vs NoSQL Architecture",
        "api": "REST & GraphQL APIs: How Web Services Communicate",
        "tcp": "TCP/IP Networking: Handshakes, Packets & Protocols",
        "dns": "How Domain Name System (DNS) Resolves Internet Addresses",
        "http": "How the HTTP & HTTPS Protocols Work Across the Web",
        "cpu": "How a Computer CPU Executes Machine Instructions",
        "gpu": "Graphics Processing Units (GPUs) & Parallel Compute Architecture",
        "ram": "Computer Memory (RAM): Architecture, Registers & Cache Hierarchy",
        "ssd": "How Solid State Drives (SSDs) & NAND Flash Memory Work"
    }

    if q_lower in short_acronyms:
        return _default_spec(short_acronyms[q_lower], "NEW_VIDEO")

    # Greetings
    greetings = ["hi", "hello", "hey", "hii", "helo", "hiya", "howdy", "sup", "yo",
                 "good morning", "good evening", "good afternoon", "namaste", "greetings"]
    q_stripped = q_lower.rstrip("!").rstrip(".").strip()
    if q_stripped in greetings or q_lower in greetings:
        return _default_spec(q, "GENERAL_CONVERSATION",
            "Hello! I am **VisuAIze** - your AI cinematic step-by-step video tutorial platform!\n\n"
            "I turn **any topic, question, or problem statement** into a full step-by-step video tutorial with dual neural narration, visual diagrams, and interactive learning checkpoints.\n\n"
            "You can ask me to visualize anything: programming languages, science, engineering, life skills, mathematics, or everyday problems. What would you like to learn today?")

    # Too short / empty
    if len(q) < 2:
        return _default_spec(q, "REJECT_UNREALISTIC")

    # Pure random gibberish (non-vowel letter mash)
    if len(q) > 6 and not any(v in q_lower for v in "aeiouy"):
        return _default_spec(q, "REJECT_UNREALISTIC")

    # Platform questions about VisuAIze itself
    platform_q = ["what is visuaize", "how does visuaize work", "what can you do",
                  "who made you", "what models", "how do you work", "what are you"]
    if any(pt in q_lower for pt in platform_q):
        return _default_spec(q, "GENERAL_CONVERSATION",
            "**VisuAIze** is an AI cinematic tutorial platform powered by:\n\n"
            "- **Pedagogical AI Engine**: Structured Problem-Analogy-Solution curriculum synthesis\n"
            "- **Dual Neural Voice Engine**: Microsoft Edge dual-host conversational narration\n"
            "- **Visual Slide & Diagram Engine**: 3D kinetic visuals and schematic node diagrams\n"
            "- **Video Assembler Engine**: Fast H.264 video rendering with Ken Burns camera motion\n\n"
            "Just describe any concept, skill, or problem, and I will generate the complete step-by-step video tutorial!")

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
            max_tokens=600
        )
        return _clean_json_obj(resp.choices[0].message.content)
    except Exception as e:
        print(f"[IntentEngine/Groq] {e}")
        return None


def _classify_with_gemini(question: str, history: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """Fallback: Intent Classification via Google Gemini (google-genai SDK)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = _build_user_prompt(question, history)
        full = f"{INTENT_SYSTEM_PROMPT}\n\n{prompt}"
        for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                resp = client.models.generate_content(model=model_name, contents=[full])
                if resp and resp.text:
                    return _clean_json_obj(resp.text)
            except Exception:
                continue
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

    # Auto-promotion: Never block valid user topic queries with CLARIFY_REQUIRED
    if spec.get("intent") == "CLARIFY_REQUIRED":
        q_clean = question.strip()
        if len(q_clean) >= 2 and not all(c in "?!.,- " for c in q_clean):
            spec["intent"] = "NEW_VIDEO"
            if not spec.get("subject") or spec["subject"].lower() in ("video", "tutorial"):
                spec["subject"] = f"Complete Guide: {q_clean.title()}"
            print(f"[IntentEngine] Auto-promoted CLARIFY_REQUIRED -> NEW_VIDEO ('{spec['subject']}')")

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
    history: Optional[List[Dict[str, Any]]] = None,
    provider: str = "groq"
) -> Dict[str, Any]:
    """
    Main entry point - implements all 4 architecture features:
      1. Intent Classification  -> classify into intents with multi-provider fallback
      2. Context Management     -> resolve follow-up against history
      3. Structured Output      -> return full JSON video spec
      4. Orchestration Ready    -> spec["intent"] drives server.py
    """
    # Feature 1a: Local heuristics (instant, zero API cost)
    local_result = _local_heuristics_classifier(question, history)
    if local_result is not None:
        _apply_spec_defaults(local_result, question)
        return local_result

    # Feature 1b: LLM classification routed by requested provider
    spec = None
    prov = (provider or "groq").lower()

    if prov == "gemini":
        spec = _classify_with_gemini(question, history)
        if spec is None:
            spec = _classify_with_groq(question, history)
    else:
        spec = _classify_with_groq(question, history)
        if spec is None:
            spec = _classify_with_gemini(question, history)

    if spec is None:
        print("[IntentEngine] All classifiers failed - defaulting to NEW_VIDEO")
        clean_subj = question.strip().title() if len(question.strip()) > 3 else "Visual Learning Tutorial"
        return _default_spec(clean_subj, "NEW_VIDEO")

    # Feature 3: Validate structured output
    _apply_spec_defaults(spec, question)

    # Feature 2: Context resolution for modification intents
    if spec.get("intent") in ("MODIFY_VIDEO", "REGENERATE_VIDEO") and history:
        _resolve_modification_context(spec, question, history)

    return spec
