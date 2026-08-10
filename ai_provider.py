"""
VisuAIze - Universal AI Provider
Supports 5 targeted models with robust automatic failovers:
  1. Groq (Llama 3.3 70B - Fastest 1-2s)
  2. Google Gemini (Gemini 2.0 Flash)
  3. Llama 3.1 (Meta Open Source 8B)
  4. Mistral (Mistral & Fast Instruct)
  5. Ollama (100% Offline Local)
"""

import json
import os
import re
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


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT TEMPLATE (shared across all providers)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Lead Visual Script Engineer for VisuAIze, a world-class AI step-by-step problem-solving video generator inspired by Google Flow, Open-Sora, and NotebookLM.

Your task: Break down any concept, problem, or question into a structured 5-step problem-solving visual tutorial:
  Step 1: Goal & Problem Setup (Define the problem & starting state clearly)
  Step 2: Core Components & Mechanism (Explain the underlying components or theory)
  Step 3: Actionable Step-by-Step Execution (Demonstrate the core procedure/solution)
  Step 4: Analysis & Optimization (Explain why it works & fine-tuning details)
  Step 5: Final Solution & Verification (Show the completed outcome & success criteria)

Return ONLY a valid JSON object (no markdown, no explanation, just pure JSON).

The root JSON object MUST have this exact structure:
{
  "steps": [
    {
      "step_number": 1,
      "title": "Short title for the step (max 6 words)",
      "narration": "Clear, engaging spoken narration explaining this problem-solving step (2-3 sentences).",
      "image_prompt": "Vivid 3D visual description for an AI image generator. Describe physical 3D objects, humanoids, cars, tools, mechanical assemblies, or scientific schematics. Do NOT include text overlay instructions in image_prompt.",
      "motion_prompt": "A cinematic 3D scene description for Open-Sora/AnimateDiff visual engine. Describe the EXACT real-world subject in motion: specific objects, materials, lighting, camera angle, and action happening in this step. Example: 'Close-up cinematic 3D render of a beating human heart with glowing red blood vessels pumping oxygenated blood through the aorta, studio lighting, photorealistic octane render, dynamic camera angle, no text'",
      "duration_seconds": 6,
      "components": [
        {
          "name": "Piston",
          "desc": "Converts combustion pressure into linear movement",
          "x": 35,
          "y": 50
        }
      ]
    }
  ],
  "quiz": {
    "question": "What is the primary function of the spark plug in Step 3?",
    "options": [
      "Ignite air-fuel mixture",
      "Pump oil",
      "Filter exhaust",
      "Cool cylinder"
    ],
    "correct_index": 0,
    "explanation": "The spark plug creates an electric spark to ignite the compressed fuel."
  }
}

Rules:
- Generate 4 to 6 logical problem-solving steps inside the "steps" array.
- For each step, include a vivid 'motion_prompt' — a real-world 3D scene showing EXACTLY what is happening in this step (used by the AI visual engine to generate a photorealistic image).
- For each step, include 1 to 4 key interactive visual components in "components" with 2D percentage coordinates (x: 0-100, y: 0-100).
- Include exactly 1 end-of-video multiple-choice "quiz" object at the root level. "correct_index" must be an integer (0-3).
- Narration must be clear, educational, and adapted to the requested complexity level (EL5, STUDENT, or EXPERT).
- Return ONLY valid JSON. No markdown fences."""


COMPLEXITY_DESCRIPTIONS = {
    "EL5": "EL5 (Explain Like I'm 5: Use simple analogies, playful conversational language, zero technical jargon, and simple visual metaphors suitable for a child or complete beginner.)",
    "STUDENT": "STUDENT (Standard Educational: Clear, structured, informative narration with helpful explanations suitable for high school or college students.)",
    "EXPERT": "EXPERT (Advanced Technical: In-depth technical breakdown using precise industry terminology, advanced mechanics, math/physics principles, and rigorous details for professionals.)"
}


def normalize_complexity(level_raw) -> str:
    if not level_raw:
        return "STUDENT"
    s = str(level_raw).upper().strip()
    if any(k in s for k in ["EL5", "ELI5", "5YO", "LIKE I'M 5", "LIKE IM 5", "CHILD", "KID", "SIMPLE", "BEGINNER", "ELEMENTARY"]):
        return "EL5"
    if any(k in s for k in ["EXPERT", "ADVANCED", "PROFESSIONAL", "PRO", "DEEP DIVE", "TECHNICAL", "MASTER"]):
        return "EXPERT"
    return "STUDENT"


def _build_user_prompt(question_or_spec) -> str:
    if isinstance(question_or_spec, dict):
        subject   = question_or_spec.get("subject") or "Tutorial"
        style     = question_or_spec.get("style") or "cinematic 3D educational"
        tone      = question_or_spec.get("tone") or "clear and friendly"

        complexity_input = (
            question_or_spec.get("complexity")
            or question_or_spec.get("complexity_level")
            or question_or_spec.get("level")
            or subject
        )
        complexity = normalize_complexity(complexity_input)

        try:
            num_steps = int(question_or_spec.get("num_steps") or 5)
            num_steps = max(4, num_steps) if num_steps > 0 else 5
        except (ValueError, TypeError):
            num_steps = 5

        mods    = question_or_spec.get("modifications", [])
        mod_str = f"\nMODIFICATIONS REQUESTED: {', '.join(mods)}" if mods else ""

        complexity_desc = COMPLEXITY_DESCRIPTIONS.get(complexity, COMPLEXITY_DESCRIPTIONS["STUDENT"])

        return f"""Create a step-by-step instructional video script with these exact specifications:

PROBLEM/SUBJECT: {subject}
VISUAL STYLE: {style}
NARRATION TONE: {tone}
COMPLEXITY LEVEL: {complexity_desc}
TARGET NUMBER OF STEPS: {num_steps}{mod_str}

Return ONLY the JSON response object containing "steps" array (with step "components") and "quiz" object. No markdown fences. No explanation text."""
    else:
        raw_text = str(question_or_spec)
        complexity = normalize_complexity(raw_text)
        complexity_desc = COMPLEXITY_DESCRIPTIONS.get(complexity, COMPLEXITY_DESCRIPTIONS["STUDENT"])

        return f"""Create a step-by-step instructional video script for:

PROBLEM/QUESTION: {raw_text}
COMPLEXITY LEVEL: {complexity_desc}

Return ONLY the JSON response object containing "steps" array (with step "components") and "quiz" object. No markdown fences. No explanation text."""


class StepList(list):
    """
    Subclass of list that holds step dictionaries while attaching the root-level `quiz` object.
    Maintains 100% backwards compatibility for callers expecting a list of steps.
    """
    def __init__(self, steps: list, quiz: dict = None):
        super().__init__(steps)
        self.quiz = quiz or {}

    def to_dict(self) -> dict:
        return {
            "steps": list(self),
            "quiz": self.quiz,
        }


DEFAULT_QUIZ = {
    "question": "What is the primary function or key takeaway of this tutorial?",
    "options": [
        "Follow the step-by-step procedure carefully",
        "Skip the core mechanism setup",
        "Disregard component alignment",
        "Execute steps in arbitrary random order"
    ],
    "correct_index": 0,
    "explanation": "Following the structured step-by-step procedure ensures correct execution and optimal results."
}


def _sanitize_component(comp, idx: int) -> dict:
    if not isinstance(comp, dict):
        return {
            "name": f"Component {idx + 1}",
            "desc": "Key operational element",
            "x": round(35.0 + (idx * 15) % 50, 1),
            "y": round(40.0 + (idx * 10) % 40, 1),
        }
    name = str(comp.get("name") or f"Component {idx + 1}")
    desc = str(comp.get("desc") or "Key visual element for this step")
    try:
        x = float(comp.get("x", 50))
        x = max(0.0, min(100.0, x))
    except (ValueError, TypeError):
        x = 50.0

    try:
        y = float(comp.get("y", 50))
        y = max(0.0, min(100.0, y))
    except (ValueError, TypeError):
        y = 50.0

    return {"name": name, "desc": desc, "x": round(x, 1), "y": round(y, 1)}


def _sanitize_step(step, idx: int) -> dict:
    if not isinstance(step, dict):
        step = {}

    step_number = step.get("step_number")
    try:
        step_number = int(step_number) if step_number is not None else idx + 1
    except (ValueError, TypeError):
        step_number = idx + 1

    title = str(step.get("title") or f"Step {step_number}: Execution")
    narration = str(step.get("narration") or f"In step {step_number}, focus on executing the primary mechanism carefully.")
    image_prompt = str(step.get("image_prompt") or f"Vivid 3D visual showing step {step_number} core procedure.")

    try:
        duration_seconds = int(step.get("duration_seconds") or 6)
        duration_seconds = max(3, min(30, duration_seconds))
    except (ValueError, TypeError):
        duration_seconds = 6

    raw_components = step.get("components")
    components = []
    if isinstance(raw_components, list) and raw_components:
        for c_idx, comp in enumerate(raw_components):
            components.append(_sanitize_component(comp, c_idx))
    else:
        comp_name = title.split(":")[0] if ":" in title else title[:20]
        components = [
            _sanitize_component({
                "name": comp_name,
                "desc": "Primary operational focal point",
                "x": 35.0,
                "y": 50.0
            }, 0)
        ]

    # Agnes pipeline: motion_prompt for Sora+AnimateDiff visual engine
    motion_prompt = str(step.get("motion_prompt") or image_prompt)

    return {
        "step_number": step_number,
        "title": title,
        "narration": narration,
        "image_prompt": image_prompt,
        "motion_prompt": motion_prompt,
        "duration_seconds": duration_seconds,
        "components": components,
    }


def _sanitize_quiz(quiz_data, steps: list) -> dict:
    if not isinstance(quiz_data, dict):
        quiz_data = {}

    question = str(quiz_data.get("question") or "")
    if not question:
        step_ref = steps[0]["title"] if steps else "this process"
        question = f"What is the primary function or key takeaway when working on {step_ref}?"

    options = quiz_data.get("options")
    if not isinstance(options, list) or len(options) < 2:
        options = list(DEFAULT_QUIZ["options"])
    else:
        options = [str(opt) for opt in options]

    correct_index = quiz_data.get("correct_index")
    try:
        correct_index = int(correct_index)
        if correct_index < 0 or correct_index >= len(options):
            correct_index = 0
    except (ValueError, TypeError):
        correct_index = 0

    explanation = str(quiz_data.get("explanation") or DEFAULT_QUIZ["explanation"])

    return {
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
    }


def _clean_json(raw: str) -> StepList:
    """Strip markdown fences and parse JSON safely into a StepList with fallback defaults."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    parsed = None

    try:
        parsed = json.loads(text)
    except Exception:
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        start_arr = text.find("[")
        end_arr = text.rfind("]")

        if start_obj != -1 and (start_arr == -1 or start_obj < start_arr) and end_obj > start_obj:
            try:
                parsed = json.loads(text[start_obj:end_obj + 1])
            except Exception:
                pass

        if parsed is None and start_arr != -1 and end_arr > start_arr:
            try:
                parsed = json.loads(text[start_arr:end_arr + 1])
            except Exception:
                pass

    steps_raw = []
    quiz_raw = None

    if isinstance(parsed, dict):
        if "steps" in parsed and isinstance(parsed["steps"], list):
            steps_raw = parsed["steps"]
        else:
            steps_raw = [v for k, v in parsed.items() if k != "quiz" and isinstance(v, dict)]
        quiz_raw = parsed.get("quiz")
    elif isinstance(parsed, list):
        steps_raw = parsed
        quiz_raw = None

    sanitized_steps = []
    if steps_raw:
        for idx, step_item in enumerate(steps_raw):
            sanitized_steps.append(_sanitize_step(step_item, idx))

    if not sanitized_steps:
        sanitized_steps = [
            _sanitize_step({
                "step_number": 1,
                "title": "Goal & Problem Setup",
                "narration": "Identify the primary objective and starting conditions clearly.",
                "image_prompt": "3D visual diagram showing initial setup and problem overview.",
                "duration_seconds": 6,
                "components": [{"name": "Setup Area", "desc": "Initial state boundary", "x": 50, "y": 50}]
            }, 0),
            _sanitize_step({
                "step_number": 2,
                "title": "Core Mechanism",
                "narration": "Understand the main operational components involved in the process.",
                "image_prompt": "3D visual schematic illustrating key internal mechanisms.",
                "duration_seconds": 6,
                "components": [{"name": "Core Engine", "desc": "Central mechanism component", "x": 40, "y": 45}]
            }, 1),
            _sanitize_step({
                "step_number": 3,
                "title": "Actionable Execution",
                "narration": "Execute the primary steps to resolve the problem efficiently.",
                "image_prompt": "3D visual demonstrating active step-by-step execution.",
                "duration_seconds": 6,
                "components": [{"name": "Control Module", "desc": "Active execution control point", "x": 60, "y": 55}]
            }, 2),
            _sanitize_step({
                "step_number": 4,
                "title": "Analysis & Verification",
                "narration": "Verify results and ensure optimal operational performance.",
                "image_prompt": "3D visual showing completed solution and verification check.",
                "duration_seconds": 6,
                "components": [{"name": "Output Sensor", "desc": "Verification and quality metric", "x": 50, "y": 60}]
            }, 3),
        ]

    sanitized_quiz = _sanitize_quiz(quiz_raw, sanitized_steps)

    return StepList(sanitized_steps, quiz=sanitized_quiz)


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
    except Exception as e:
        last_err = e

    # Fallback to Groq if Gemini is rate limited
    try:
        return _generate_groq(question, image_path)
    except Exception:
        raise RuntimeError(f"Gemini API error: {last_err}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. LLAMA 3.1 (Meta Open Source)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_llama31(question: str, image_path: str = None) -> list:
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
            print(f"      [WARN] Groq Llama 3.1: {e}")

    # Fallback to HuggingFace
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if hf_key:
        try:
            import huggingface_hub
            hf_models = [
                "meta-llama/Llama-3.2-3B-Instruct",
                "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "Qwen/Qwen2.5-72B-Instruct",
            ]
            client = huggingface_hub.InferenceClient(token=hf_key)
            for model in hf_models:
                try:
                    res = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": _build_user_prompt(question)},
                        ],
                        max_tokens=4096,
                        temperature=0.7,
                    )
                    return _clean_json(res.choices[0].message.content)
                except Exception:
                    pass
        except Exception:
            pass

    return _generate_groq(question, image_path)


# ─────────────────────────────────────────────────────────────────────────────
# 4. MISTRAL (Mistral 7B & NeMo)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_mistral(question: str, image_path: str = None) -> list:
    # 1. Try Groq fast endpoint
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
            print(f"      [WARN] Groq Mistral fallback: {e}")

    # 2. Try Hugging Face
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if hf_key:
        try:
            import huggingface_hub
            client = huggingface_hub.InferenceClient(token=hf_key)
            res = client.chat.completions.create(
                model="meta-llama/Llama-3.2-3B-Instruct",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(question)},
                ],
                max_tokens=4096,
                temperature=0.7,
            )
            return _clean_json(res.choices[0].message.content)
        except Exception as e:
            print(f"      [WARN] HF Mistral error: {e}")

    return _generate_groq(question, image_path)


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
        print(f"      [Ollama] Auto-selected available model: {model}")

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

    print(f"      [Ollama] Generating with local model: {model}")
    response = req.post(f"{base_url}/api/chat", json=payload, timeout=300)

    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:300]}")

    content = response.json()["message"]["content"]
    return _clean_json(content)


_VALIDATION_SYSTEM = (
    "You are the input validator for VisuAIze, an AI step-by-step tutorial video generator.\n\n"
    "Your job: determine if the user input is a valid topic for an educational step-by-step tutorial video.\n\n"
    "VALID: How-to questions, concepts to explain, skills to teach, processes, problem solving, any real learnable topic.\n"
    "INVALID: Random letters (A or B or C), filler words (Hello, Hi, OK, Yes, No, test), gibberish (asdf, 1234), pure symbols.\n\n"
    "When valid, also refine the phrasing if needed (e.g. 'java' -> 'Java Programming Fundamentals').\n\n"
    'Respond ONLY with JSON, no markdown:\n'
    '{"valid": true, "reason": "", "refined_topic": "<improved or original topic>"}\n'
    'or\n'
    '{"valid": false, "reason": "<friendly explanation + example prompt>", "refined_topic": ""}'
)


def _parse_json_obj(raw: str) -> dict:
    """Extract a JSON object from raw LLM text."""
    import re as _re, json as _json
    text = raw.strip()
    text = _re.sub(r"^```(?:json)?\s*", "", text)
    text = _re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return _json.loads(text)


def _local_validate(question: str):
    """Fast local validation. Returns result dict if clearly invalid, else None."""
    q = question.strip()
    q_lower = q.lower()
    
    # Valid short technical terms
    if q_lower in ("ai", "ml", "dl", "c", "c++", "go", "js", "ts", "py", "sql", "git", "vr", "ar", "ui", "ux", "3d", "db", "os", "api"):
        return None

    if len(q) < 2:
        return {
            "valid": False,
            "reason": "Please enter a topic or problem statement to visualize.",
            "refined_topic": "",
        }
    words = q.split()
    # Pure greetings / filler words
    _fillers = {"hello", "hi", "hey", "ok", "okay", "yes", "no", "test",
                "testing", "check", "ping", "sup", "yo", "hola", "greetings"}
    if len(words) <= 2 and all(w.lower().strip("!?.") in _fillers for w in words):
        return {
            "valid": False,
            "reason": f"'{q}' is a greeting. Describe what concept or problem you'd like to learn!",
            "refined_topic": "",
        }
    # Pure symbols / numbers
    if not any(c.isalpha() for c in q):
        return {
            "valid": False,
            "reason": "Please describe a real topic or question (e.g. 'How do neural networks work?').",
            "refined_topic": "",
        }
    # Gibberish: very high ratio of non-alphabetic chars
    alpha_ratio = sum(c.isalpha() for c in q) / max(len(q), 1)
    if alpha_ratio < 0.35 and len(q) > 6:
        return {
            "valid": False,
            "reason": "That input looks like random characters. Please describe a learning topic.",
            "refined_topic": "",
        }
    return None   # uncertain — let AI decide


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
    "huggingface": ("Llama 3.1", _generate_llama31),
    "hf": ("Llama 3.1", _generate_llama31),
}


def generate_steps(question: str, image_path: str = None) -> list:
    provider_key = os.getenv("AI_PROVIDER", "groq").lower().strip()

    if provider_key not in PROVIDERS:
        provider_key = "groq"

    provider_name, provider_fn = PROVIDERS[provider_key]
    print(f"[AI] Using Provider: {provider_name}")

    if image_path:
        print(f"   [Image] Context: {image_path}")

    steps = provider_fn(question, image_path)

    print(f"[OK] Generated {len(steps)} steps successfully!")
    for step in steps:
        print(f"   {step['step_number']}. {step['title']}")

    return steps


def list_providers() -> dict:
    return {
        "groq": {"name": "Groq API", "desc": "Llama 3.3 · Ultra Fast (1-2s)", "tag": "Fast"},
        "gemini": {"name": "Google Gemini", "desc": "Gemini 2.0 Flash · Deep Reasoning", "tag": "Pro"},
        "llama31": {"name": "Llama 3.1", "desc": "Meta Open Source 8B", "tag": "Open"},
        "mistral": {"name": "Mistral", "desc": "Mistral 7B & NeMo Instruct", "tag": "Smart"},
        "ollama": {"name": "Ollama Local", "desc": "100% Offline on your PC", "tag": "Offline"},
    }


def validate_prompt(question: str) -> dict:
    """
    Claude/ChatGPT-style input intelligence.
    1. Fast local check (instant, no API)
    2. AI-powered deep validation (Groq if available)
    Returns: {"valid": bool, "reason": str, "refined_topic": str}
    """
    local_result = _local_validate(question)
    if local_result is not None:
        return local_result

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"valid": True, "reason": "", "refined_topic": question}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": _VALIDATION_SYSTEM},
                {"role": "user",   "content": 'User input: "' + question + '"'},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        result = _parse_json_obj(resp.choices[0].message.content)
        return {
            "valid":         bool(result.get("valid", True)),
            "reason":        result.get("reason", ""),
            "refined_topic": result.get("refined_topic", question) or question,
        }
    except Exception as e:
        print(f"[Validation] AI check skipped: {e}")
        return {"valid": True, "reason": "", "refined_topic": question}
