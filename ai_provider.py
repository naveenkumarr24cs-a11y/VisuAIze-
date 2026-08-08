"""
VisuAIze - Universal AI Provider
Supports 5 targeted models:
  1. Groq (Llama 3.3 70B - Fastest 1-2s)
  2. Google Gemini (Gemini 2.0 Flash)
  3. Llama 3.1 (Meta Open Source 8B/70B)
  4. Mistral (Mistral 7B / NeMo Instruct)
  5. Ollama (100% Offline Local)
"""

import json
import os
import re
import base64
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT TEMPLATE (shared across all providers)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert instructional video script writer for VisuAIze.
Your task is to break down any question, problem, or task into clear, visual, step-by-step instructions.

Return ONLY a valid JSON array (no markdown, no explanation, just pure JSON).
Each step must have exactly these fields:
{
  "step_number": 1,
  "title": "Short title for the step (max 6 words)",
  "narration": "Clear, friendly spoken narration for this step. 1-3 sentences. This is what the AI voice will say.",
  "image_prompt": "Detailed visual description for an AI image generator. Describe exactly what should be shown visually. Be specific about style.",
  "duration_seconds": 7
}

Rules:
- Generate between 5 and 8 steps (not more, not less)
- Narration should be conversational and encouraging
- Image prompts should be detailed, clear, and visually descriptive
- Each step should be logically ordered
- Duration should be 6-10 seconds per step based on narration length
- The final step should always be a completion/result step
- Return ONLY the JSON array. No markdown. No explanation."""


def _build_user_prompt(question: str) -> str:
    return f"""Create a step-by-step instructional video script for:

PROBLEM/QUESTION: {question}

Return ONLY the JSON array. No markdown fences. No explanation text."""


def _clean_json(raw: str) -> list:
    """Strip markdown fences and parse JSON."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ─────────────────────────────────────────────────────────────────────────────
# 1. GROQ API (Llama 3.3 70B - Ultra Fast)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_groq(question: str, image_path: str = None) -> list:
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env — get one free at https://console.groq.com")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=api_key)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if image_path and Path(image_path).exists():
        vision_model = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = Path(image_path).suffix.lower().replace(".", "")
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{image_b64}"}},
                {"type": "text", "text": _build_user_prompt(question)},
            ],
        })
        model = vision_model
    else:
        messages.append({"role": "user", "content": _build_user_prompt(question)})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=4096,
    )
    return _clean_json(response.choices[0].message.content)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GOOGLE GEMINI (Gemini 2.0 Flash)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_gemini(question: str, image_path: str = None) -> list:
    import time
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    user_prompt = _build_user_prompt(question)
    models_to_try = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    last_err = None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for m_name in models_to_try:
            for attempt in range(2):
                try:
                    res = client.models.generate_content(
                        model=m_name,
                        contents=[SYSTEM_PROMPT, user_prompt]
                    )
                    if res.text:
                        return _clean_json(res.text)
                except Exception as e:
                    last_err = e
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        time.sleep(2)
                    else:
                        break
    except ImportError:
        pass

    import google.generativeai as legacy_genai
    legacy_genai.configure(api_key=api_key)
    parts = [SYSTEM_PROMPT, user_prompt]

    for m_name in models_to_try:
        try:
            model = legacy_genai.GenerativeModel(m_name)
            response = model.generate_content(parts)
            return _clean_json(response.text)
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Gemini API error: {last_err}. Try using Groq model instead.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. LLAMA 3.1 (Meta Open Source)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_llama31(question: str, image_path: str = None) -> list:
    # Try Groq llama-3.1-8b-instant first if available, then fallback to HuggingFace
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(question)}
            ]
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return _clean_json(response.choices[0].message.content)
        except Exception as e:
            print(f"      ⚠️ Groq Llama 3.1 fallback to HuggingFace: {e}")

    # Fallback to HuggingFace
    import huggingface_hub
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_key:
        raise ValueError("HUGGINGFACE_API_KEY or GROQ_API_KEY needed for Llama 3.1")

    client = huggingface_hub.InferenceClient(token=hf_key)
    res = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question)},
        ],
        max_tokens=4096,
        temperature=0.7,
    )
    return _clean_json(res.choices[0].message.content)


# ─────────────────────────────────────────────────────────────────────────────
# 4. MISTRAL (Mistral 7B / NeMo)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_mistral(question: str, image_path: str = None) -> list:
    # Try Groq mixtral-8x7b-32768 first, then HuggingFace
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(question)}
            ]
            response = client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return _clean_json(response.choices[0].message.content)
        except Exception as e:
            print(f"      ⚠️ Groq Mistral fallback: {e}")

    # Hugging Face Mistral
    import huggingface_hub
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_key:
        raise ValueError("HUGGINGFACE_API_KEY or GROQ_API_KEY needed for Mistral")

    client = huggingface_hub.InferenceClient(token=hf_key)
    res = client.chat.completions.create(
        model="mistralai/Mistral-7B-Instruct-v0.3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question)},
        ],
        max_tokens=4096,
        temperature=0.7,
    )
    return _clean_json(res.choices[0].message.content)


# ─────────────────────────────────────────────────────────────────────────────
# 5. OLLAMA (100% Local, Offline, Free)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_ollama(question: str, image_path: str = None) -> list:
    import requests as req

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    configured_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    try:
        health = req.get(f"{base_url}/api/tags", timeout=5)
        if health.status_code != 200:
            raise ConnectionError()
        installed_models = [m["name"] for m in health.json().get("models", [])]
    except Exception:
        raise RuntimeError(
            "Ollama is not running. Please launch the Ollama app on your computer or run 'ollama run llama3.2' in terminal."
        )

    if not installed_models:
        raise RuntimeError(
            "No models installed in Ollama yet. Open PowerShell and run: ollama run llama3.2"
        )

    if configured_model in installed_models or any(configured_model in m for m in installed_models):
        model = configured_model
    else:
        model = installed_models[0]
        print(f"      🦙 Auto-selected available Ollama model: {model}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(question)}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 4096,
        },
    }

    print(f"      🦙 Generating with local model: {model}")
    response = req.post(f"{base_url}/api/chat", json=payload, timeout=300)

    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:300]}")

    content = response.json()["message"]["content"]
    return _clean_json(content)


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS = {
    "groq": ("Groq API (Llama 3.3)", _generate_groq),
    "gemini": ("Google Gemini", _generate_gemini),
    "llama31": ("Llama 3.1", _generate_llama31),
    "llama": ("Llama 3.1", _generate_llama31),
    "mistral": ("Mistral AI", _generate_mistral),
    "ollama": ("Ollama (Local)", _generate_ollama),
    # Aliases
    "huggingface": ("Llama 3.1", _generate_llama31),
    "hf": ("Llama 3.1", _generate_llama31),
}


def generate_steps(question: str, image_path: str = None) -> list:
    provider_key = os.getenv("AI_PROVIDER", "groq").lower().strip()

    if provider_key not in PROVIDERS:
        provider_key = "groq"

    provider_name, provider_fn = PROVIDERS[provider_key]
    print(f"🧠 Using AI Provider: {provider_name}")

    if image_path:
        print(f"   📎 Image context: {image_path}")

    steps = provider_fn(question, image_path)

    print(f"✅ Generated {len(steps)} steps successfully!")
    for step in steps:
        print(f"   {step['step_number']}. {step['title']}")

    return steps


def list_providers() -> dict:
    return {
        "groq": {"name": "Groq API", "desc": "Llama 3.3 · Ultra Fast (1-2s)", "tag": "Fast"},
        "gemini": {"name": "Google Gemini", "desc": "Gemini 2.0 Flash · Deep Reasoning", "tag": "Pro"},
        "llama31": {"name": "Llama 3.1", "desc": "Meta Open Source 8B/70B", "tag": "Open"},
        "mistral": {"name": "Mistral", "desc": "Mistral 7B & NeMo Instruct", "tag": "Fast"},
        "ollama": {"name": "Ollama Local", "desc": "100% Offline on your PC", "tag": "Offline"},
    }
