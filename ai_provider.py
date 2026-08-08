"""
VisuAIze - Universal AI Provider
Supports multiple AI backends:
  - Google Gemini (default)
  - Groq API (Llama 3, Mixtral - very fast)
  - Hugging Face Inference API (1000s of models)
  - Ollama (100% local, no internet, free)

Switch providers by changing AI_PROVIDER in your .env file.
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
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first [ and last ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER: GOOGLE GEMINI
# ─────────────────────────────────────────────────────────────────────────────

def _generate_gemini(question: str, image_path: str = None) -> list:
    import time
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    user_prompt = _build_user_prompt(question)
    models_to_try = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3.6-flash", "gemini-1.5-flash"]
    
    last_err = None

    # Try official new google.genai SDK first
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
                        print(f"      ⚠️  Gemini {m_name} rate limited. Waiting 2s...")
                        time.sleep(2)
                    else:
                        print(f"      ⚠️  Gemini {m_name} error: {e}")
                        break
    except ImportError:
        pass

    # Fallback to legacy google.generativeai SDK
    import google.generativeai as legacy_genai
    legacy_genai.configure(api_key=api_key)
    parts = [SYSTEM_PROMPT, user_prompt]

    for m_name in models_to_try:
        for attempt in range(2):
            try:
                model = legacy_genai.GenerativeModel(m_name)
                response = model.generate_content(parts)
                return _clean_json(response.text)
            except Exception as e:
                last_err = e
                if "429" in str(e):
                    time.sleep(2)
                else:
                    break

    raise RuntimeError(f"Gemini API error: {last_err}. Try using Groq model instead.")


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER: GROQ API
# ─────────────────────────────────────────────────────────────────────────────

def _generate_groq(question: str, image_path: str = None) -> list:
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env — get one free at https://console.groq.com")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # Groq supports vision with llava models
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
        # Use vision model when image is provided
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
# PROVIDER: HUGGING FACE INFERENCE API
# ─────────────────────────────────────────────────────────────────────────────

def _generate_huggingface(question: str, image_path: str = None) -> list:
    import huggingface_hub

    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        raise ValueError("HUGGINGFACE_API_KEY not set in .env — get one free at https://huggingface.co/settings/tokens")

    models_to_try = [
        "meta-llama/Llama-3.2-3B-Instruct",
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen2.5-72B-Instruct",
    ]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(question)},
    ]

    client = huggingface_hub.InferenceClient(token=api_key)
    last_err = None

    for model in models_to_try:
        try:
            print(f"      🤗 Trying HuggingFace model: {model}")
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
            )
            content = res.choices[0].message.content
            return _clean_json(content)
        except Exception as e:
            last_err = e
            print(f"      ⚠️  HF model {model} failed: {e}. Trying fallback model...")

    raise RuntimeError(f"HuggingFace error: {last_err}")


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER: OLLAMA (local, 100% offline, free)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_ollama(question: str, image_path: str = None) -> list:
    import requests as req

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    configured_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    # 1. Verify Ollama is running and check downloaded models
    try:
        health = req.get(f"{base_url}/api/tags", timeout=5)
        if health.status_code != 200:
            raise ConnectionError()
        installed_models = [m["name"] for m in health.json().get("models", [])]
    except Exception:
        raise RuntimeError(
            f"Ollama is not running. Please launch the Ollama app on your computer or start it in terminal."
        )

    if not installed_models:
        raise RuntimeError(
            "No models installed in Ollama yet.\n"
            "To use Ollama for free, open PowerShell and run:\n"
            "   ollama run llama3.2\n"
            "(Once downloaded, refresh this page and click generate!)"
        )

    # 2. Pick configured model or the first available model
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
    response = req.post(
        f"{base_url}/api/chat",
        json=payload,
        timeout=300,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:300]}")

    content = response.json()["message"]["content"]
    return _clean_json(content)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS = {
    "gemini": ("Google Gemini", _generate_gemini),
    "groq": ("Groq API", _generate_groq),
    "huggingface": ("Hugging Face", _generate_huggingface),
    "hf": ("Hugging Face", _generate_huggingface),  # alias
    "ollama": ("Ollama (Local)", _generate_ollama),
}


def generate_steps(question: str, image_path: str = None) -> list:
    """
    Generate step-by-step instructions using the configured AI provider.

    Provider is set via AI_PROVIDER in .env:
      AI_PROVIDER=gemini       → Google Gemini (default)
      AI_PROVIDER=groq         → Groq API (fastest)
      AI_PROVIDER=huggingface  → Hugging Face Inference API
      AI_PROVIDER=ollama       → Local Ollama (offline)
    """
    provider_key = os.getenv("AI_PROVIDER", "gemini").lower().strip()

    if provider_key not in PROVIDERS:
        valid = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown AI_PROVIDER '{provider_key}'. Valid options: {valid}")

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
    """Returns info about all available providers."""
    return {
        "gemini": {
            "name": "Google Gemini",
            "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "env_key": "GEMINI_API_KEY",
            "free_tier": True,
            "local": False,
            "vision": True,
            "get_key": "https://aistudio.google.com/app/apikey",
        },
        "groq": {
            "name": "Groq API",
            "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
            "env_key": "GROQ_API_KEY",
            "free_tier": True,
            "local": False,
            "vision": True,
            "get_key": "https://console.groq.com",
        },
        "huggingface": {
            "name": "Hugging Face Inference API",
            "models": ["meta-llama/Meta-Llama-3.1-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3",
                       "microsoft/Phi-3-mini-4k-instruct", "Qwen/Qwen2.5-72B-Instruct"],
            "env_key": "HUGGINGFACE_API_KEY",
            "free_tier": True,
            "local": False,
            "vision": True,
            "get_key": "https://huggingface.co/settings/tokens",
        },
        "ollama": {
            "name": "Ollama (Local)",
            "models": ["llama3.2", "llama3.1", "mistral", "phi3", "gemma2", "qwen2.5"],
            "env_key": None,
            "free_tier": True,
            "local": True,
            "vision": True,
            "get_key": "https://ollama.com/download",
        },
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("VisuAIze — AI Provider Test")
    print("=" * 60)

    provider = os.getenv("AI_PROVIDER", "gemini")
    print(f"Current provider: {provider}")

    steps = generate_steps("How do I make a cup of tea?")
    print(f"\nFirst step: {steps[0]['title']}")
    print(f"Narration preview: {steps[0]['narration'][:100]}...")
