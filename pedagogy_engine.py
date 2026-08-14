"""
VisuAIze - Pedagogy Engine (NotebookLM-Style 3-Arc Problem-Solving Script Generator)
=====================================================================================
Implements the elite 3-arc pedagogical problem-solving structure:
  Arc 1 - PROBLEM HOOK: Vivid, relatable real-world dilemma, friction, failure mode, or counter-intuitive puzzle.
  Arc 2 - ANALOGY BRIDGE: Concrete, intuitive physical metaphor that makes the core concept immediately click.
  Arc 3 - STEP-BY-STEP RESOLUTION: 3-5 progressive solution steps with clear visual milestones.

Dual-Speaker Dialogue:
  TEACHER: Confident, warm, authoritative, structured explanation.
  STUDENT: Curious, energetic, asks natural questions that the audience is thinking.

Rich Visual Prompts:
  Tailored specifically for Nano Banana FLUX image generation (specifying subjects,
  3D anatomical/mechanical detail, volumetric lighting, and cinematic composition).

Model Fallbacks:
  Gemini: gemini-flash-latest, gemini-3.5-flash, gemini-3.1-flash-lite, gemini-pro-latest
  Groq: llama-3.3-70b-versatile
"""

import os
import sys
import json
import re
import traceback
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

# Optional dependencies for API calls
try:
    import requests
except ImportError:
    requests = None

try:
    from google import genai as google_genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    google_genai = None
    GOOGLE_GENAI_AVAILABLE = False


# ============================================================================
# SYSTEM PROMPT DEFINITION (ELITE 3-ARC PROBLEM-SOLVING FRAMEWORK)
# ============================================================================

PEDAGOGICAL_SYSTEM_PROMPT = """You are an elite masterclass educational scriptwriter and animator specializing in the NotebookLM / 3Blue1Brown 3-Arc Problem-Solving Framework. Your mission is to produce a captivating, dual-speaker educational script that makes complex concepts instantly intuitive through visual storytelling.

You MUST enforce this strict 3-arc structure:

1. ARC 1 - PROBLEM HOOK (The Real-World Dilemma / Friction / Puzzle):
   - Open with a vivid, relatable real-world dilemma, mechanical friction, failure mode, or counter-intuitive paradox.
   - Establish why this problem matters and what makes it tricky or counter-intuitive.
   - TEACHER presents the core tension with warmth and authority.
   - STUDENT reacts with relatable curiosity or confusion, articulating what the audience is wondering.

2. ARC 2 - ANALOGY BRIDGE (The Intuitive Physical Metaphor):
   - Bridge the problem to a concrete, tangible physical metaphor (e.g. dual-stage pump, city water tower, one-way hydraulic check valve, traffic roundabout).
   - Create the instant "Aha!" epiphany where the mental model clicks into place.
   - TEACHER guides the metaphor clearly and concisely.
   - STUDENT experiences the revelation and confirms the key insight.

3. ARC 3 - STEP-BY-STEP RESOLUTION (3 to 5 Progressive Milestones):
   - Break down the solution into 3 to 5 progressive, sequential milestones.
   - Each step must build logically upon the previous one with clear visual milestones.
   - TEACHER provides structured, authoritative explanations of mechanics and flow.
   - STUDENT asks sharp clarifying questions or validates the mechanism.

DUAL-SPEAKER DIALOGUE RULES:
- TEACHER: Confident, warm, authoritative, structured explanation. Speaks clearly and concisely without jargon overload.
- STUDENT: Curious, energetic, asks natural questions that the audience is thinking, expresses relatable intuition.

NANO BANANA FLUX VISUAL PROMPT REQUIREMENTS:
For EVERY step (hook, analogy, and each solution step), provide a rich, hyper-detailed `visual_prompt` specifically tailored for Nano Banana FLUX image generation:
- Specify exact subject matters and focal elements (e.g. 3D cutaway cross-section, translucent chambers, glowing directional flow lines).
- Specify 3D anatomical / mechanical / schematic details (e.g. valve flaps, muscle walls, pressure gradients, glowing particle streams).
- Specify studio lighting (e.g. volumetric rim lighting, cinematic studio backlighting, glowing bioluminescent tracer particles, high contrast HDR).
- Specify composition and camera framing (e.g. dynamic 45-degree isometric view, cinematic macro cutaway, clean composition, 8k octane render aesthetic, no blur, no text watermark).

OUTPUT FORMAT:
You MUST respond with valid JSON ONLY. No markdown code fences, no conversational preamble, no trailing commentary. Return exactly a JSON object matching this schema:

{
  "title": "Engaging & Descriptive Title",
  "visual_style": "<inject_visual_style>",
  "problem_hook": {
    "hook_text": "The gripping dilemma, friction, or counter-intuitive puzzle",
    "teacher_line": "Teacher: The core problem statement or paradox explained warmly.",
    "student_line": "Student: Wait, so why doesn't [the intuitive thing] work?",
    "visual_prompt": "Hyper-detailed Nano Banana FLUX prompt: 3D cutaway visualization of the problem dilemma, volumetric rim lighting, dramatic high-contrast lighting, 8k octane render aesthetic, cinematic composition.",
    "motion_hint": "Slow dramatic zoom in on the focal bottleneck, shallow depth of field",
    "duration_seconds": 6
  },
  "analogy_bridge": {
    "analogy_text": "The concrete physical metaphor headline",
    "teacher_line": "Teacher: Think of it like a [concrete physical system]. Here's how it works...",
    "student_line": "Student: Oh! So [Part A] handles the incoming flow while [Part B] does the heavy lifting?!",
    "visual_prompt": "Hyper-detailed Nano Banana FLUX prompt: 3D mechanical/physical metaphor system in action, glowing fluid pathways, clean studio lighting, isometric 45-degree angle, highly detailed 8k render.",
    "motion_hint": "Smooth orbital pan around the mechanical metaphor, glowing particle dynamics",
    "duration_seconds": 6
  },
  "solution_steps": [
    {
      "step_number": 1,
      "title": "Progressive Milestone 1 Title",
      "teacher_line": "Teacher: Step 1 explanation with authoritative clarity.",
      "student_line": "Student: Quick clarifying question or realization.",
      "visual_prompt": "Hyper-detailed Nano Banana FLUX prompt: 3D anatomical/mechanical cross-section of milestone 1, glowing directional flow indicators, volumetric rim lighting, 8k octane render.",
      "motion_hint": "Camera tracking along the glowing flow pathway",
      "duration_seconds": 5,
      "components": [
        {"name": "Key Component", "desc": "Role in this step", "x": 0.5, "y": 0.5}
      ]
    },
    {
      "step_number": 2,
      "title": "Progressive Milestone 2 Title",
      "teacher_line": "Teacher: Step 2 progressive explanation.",
      "student_line": "Student: Response connecting step 1 to step 2.",
      "visual_prompt": "Hyper-detailed Nano Banana FLUX prompt: 3D cross-section showing milestone 2 mechanism, cinematic lighting, 8k render.",
      "motion_hint": "Dynamic push into the active chamber",
      "duration_seconds": 5,
      "components": [
        {"name": "Second Component", "desc": "Role in this step", "x": 0.4, "y": 0.6}
      ]
    },
    {
      "step_number": 3,
      "title": "Progressive Milestone 3 Title",
      "teacher_line": "Teacher: Step 3 progressive explanation.",
      "student_line": "Student: Realization of the complete cycle.",
      "visual_prompt": "Hyper-detailed Nano Banana FLUX prompt: 3D cross-section of milestone 3, glowing pressure dynamics, studio lighting, 8k render.",
      "motion_hint": "Wide reveal of the full circulating cycle",
      "duration_seconds": 5,
      "components": [
        {"name": "Third Component", "desc": "Role in this step", "x": 0.6, "y": 0.4}
      ]
    }
  ],
  "quiz": {
    "question": "A sharp conceptual check testing the core mechanism?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "Clear explanation of why this answer is correct."
  }
}

Ensure there are between 3 and 5 progressive solution_steps. Target complexity level: <inject_complexity>.
"""


# ============================================================================
# UTILITY FUNCTIONS & JSON PARSER
# ============================================================================

def _clean_json_response(text: str) -> str:
    """Strips markdown code fences and isolates valid JSON from LLM output."""
    if not text:
        return "{}"
    text = text.strip()
    
    # Strip markdown code blocks
    if "```json" in text:
        parts = text.split("```json")
        if len(parts) > 1:
            sub = parts[1].split("```")[0]
            text = sub.strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            sub = parts[1].split("```")[0]
            text = sub.strip()
            
    # Extract the outermost JSON object if surrounded by preamble
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
        
    return text.strip()


def _get_fallback_script(topic: str, visual_style: str = "classic") -> dict:
    """Provides a high-quality, structured fallback script adhering to the 3-arc framework."""
    clean_topic = topic.strip().title()
    return {
        "title": f"How {clean_topic} Works: The Complete Breakdown",
        "visual_style": visual_style,
        "problem_hook": {
            "hook_text": f"The Core Dilemma: Why Is {clean_topic} So Difficult to Balance?",
            "teacher_line": f"Have you ever wondered how {clean_topic} maintains seamless continuous operation without breaking down under constant pressure?",
            "student_line": "Honestly, it always felt like a black box with so many moving parts working simultaneously!",
            "visual_prompt": f"Detailed 3D cutaway schematic of {clean_topic}, dramatic volumetric rim lighting, high-contrast glowing stress points, cinematic deep obsidian background, 8k octane render aesthetic, 16:9 widescreen composition",
            "motion_hint": "Slow dramatic push-in on the primary bottleneck, subtle glowing pulse",
            "duration_seconds": 6
        },
        "analogy_bridge": {
            "analogy_text": f"The Master Analogy: The Synchronized Dual-Stage Pump System",
            "teacher_line": f"Think of {clean_topic} like a precision-engineered dual-stage hydraulic pump. One side manages intake while the other drives high-pressure output.",
            "student_line": "Oh! So instead of one massive chaotic process, it's two coordinated loops working in harmony!",
            "visual_prompt": f"A gleaming 3D mechanical dual-circuit hydraulic pump metaphor for {clean_topic}, glowing translucent tubes, cyan and amber fluid streams, studio lighting, isometric 45-degree angle, 8k render",
            "motion_hint": "Smooth orbital pan highlighting the dual-loop flow dynamics",
            "duration_seconds": 6
        },
        "solution_steps": [
            {
                "step_number": 1,
                "title": "Phase 1: Inflow & Pressure Regulation",
                "teacher_line": f"In the first phase of {clean_topic}, incoming flow enters the primary chamber where one-way valves prevent backflow and regulate baseline pressure.",
                "student_line": "Got it! So the one-way valves guarantee that everything travels in a single forward direction.",
                "visual_prompt": f"3D anatomical cross-section of {clean_topic} during intake phase, glowing blue tracer particles moving through one-way valve gates, volumetric studio lighting, crisp macro cutaway, 8k octane render",
                "motion_hint": "Camera tracks blue glowing tracer particles through the intake valve",
                "duration_seconds": 5,
                "components": [
                    {"name": "Intake Chamber", "desc": "Receives baseline inflow", "x": 0.35, "y": 0.45},
                    {"name": "One-Way Valve", "desc": "Prevents reverse backflow", "x": 0.50, "y": 0.60}
                ]
            },
            {
                "step_number": 2,
                "title": "Phase 2: Synchronized Activation & Compression",
                "teacher_line": "Next, a coordinated electrical impulse triggers uniform muscular compression, rapidly building propulsion pressure.",
                "student_line": "So the electrical timing has to be perfectly synchronized to squeeze the chamber efficiently!",
                "visual_prompt": f"3D visualization of electrical activation waves rippling across the chamber walls of {clean_topic}, glowing golden conduction fibers, cinematic rim lighting, 8k hyper-detailed render",
                "motion_hint": "Pulsating contraction motion with glowing wave propagation",
                "duration_seconds": 5,
                "components": [
                    {"name": "Conduction Pathway", "desc": "Transmits electrical impulse", "x": 0.45, "y": 0.35},
                    {"name": "Contractile Wall", "desc": "Generates pumping force", "x": 0.65, "y": 0.55}
                ]
            },
            {
                "step_number": 3,
                "title": "Phase 3: High-Pressure Distribution & Systemic Ejection",
                "teacher_line": "Finally, the pressurized outflow is ejected into the arterial network, delivering oxygen and energy across the entire system.",
                "student_line": "And the entire cycle resets instantly, ready for the next beat!",
                "visual_prompt": f"3D cross-section showing powerful oxygenated blood ejection through the outflow arch of {clean_topic}, glowing crimson arterial stream, volumetric lens flare, dramatic studio render",
                "motion_hint": "Wide cinematic zoom-out revealing continuous systemic circulation",
                "duration_seconds": 5,
                "components": [
                    {"name": "Outflow Conduit", "desc": "Channels pressurized flow", "x": 0.55, "y": 0.25},
                    {"name": "Distribution Loop", "desc": "Supplies systemic network", "x": 0.70, "y": 0.50}
                ]
            }
        ],
        "quiz": {
            "question": f"What is the primary mechanism ensuring unidirectional forward flow in {clean_topic}?",
            "options": [
                "Synchronized one-way valves that prevent backflow",
                "Random pressure fluctuations throughout the chambers",
                "Continuous manual external compression",
                "Passive gravitational drainage without resistance"
            ],
            "correct_index": 0,
            "explanation": "Unidirectional flow is maintained by precision one-way valves that open during forward pressure and seal tightly against backflow."
        }
    }


# ============================================================================
# API CALLERS (WITH STRICT FALLBACK CASCADES)
# ============================================================================

def _call_gemini_api(prompt: str, system_prompt: str) -> str:
    """
    Calls Google Gemini API using google-genai SDK.
    Fallback cascade: gemini-flash-latest -> gemini-3.5-flash -> gemini-3.1-flash-lite -> gemini-pro-latest.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    if not GOOGLE_GENAI_AVAILABLE or google_genai is None:
        raise ImportError("google-genai library is not installed. Run: pip install google-genai")

    client = google_genai.Client(api_key=api_key)
    full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{prompt}"

    gemini_models = [
        "gemini-flash-latest",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-pro-latest",
        "gemini-2.5-flash"
    ]

    last_err = None
    for model_name in gemini_models:
        try:
            print(f"🤖 [Gemini] Trying model '{model_name}'...")
            response = client.models.generate_content(
                model=model_name,
                contents=[full_prompt]
            )
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"⚠️ [Gemini] Model '{model_name}' failed: {e}")
            last_err = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def _call_groq_api(prompt: str, system_prompt: str) -> str:
    """
    Calls the Groq API directly via REST endpoint with JSON mode.
    Primary model: llama-3.3-70b-versatile.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set.")

    if requests is None:
        raise ImportError("requests library is not installed, cannot call Groq REST API.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    groq_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama3-70b-8192"
    ]

    last_err = None
    for model in groq_models:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"}
            }

            print(f"🦙 [Groq] Calling model '{model}'...")
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=35
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if content:
                return content
        except Exception as e:
            print(f"⚠️ [Groq] Model '{model}' error: {e}")
            last_err = e
            continue

    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


def _call_huggingface_api(prompt: str, system_prompt: str) -> str:
    """Calls Hugging Face Inference API."""
    api_key = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_VIDEO_TOKEN")
    if not api_key:
        raise ValueError("HUGGINGFACE_API_KEY not set.")
    model = os.getenv("HF_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "inputs": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
        "parameters": {"max_new_tokens": 2500, "temperature": 0.7, "return_full_text": False}
    }
    res = requests.post(f"https://api-inference.huggingface.co/models/{model}", headers=headers, json=payload, timeout=40)
    res.raise_for_status()
    data = res.json()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"]
    return str(data)


def _call_mistral_api(prompt: str, system_prompt: str) -> str:
    """Calls Mistral API or falls back to Groq."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return _call_groq_api(prompt, system_prompt)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "mistral-small-latest",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2500,
        "response_format": {"type": "json_object"}
    }
    res = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


def _call_ollama_api(prompt: str, system_prompt: str) -> str:
    """Calls local Ollama instance."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "stream": False,
        "format": "json"
    }
    res = requests.post(f"{base_url}/api/chat", json=payload, timeout=60)
    res.raise_for_status()
    return res.json().get("message", {}).get("content", "")


# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

def generate_pedagogical_script(
    topic: str,
    visual_style: str = "classic",
    complexity: str = "STUDENT",
    provider: str = "groq"
) -> dict:
    """
    Generates a structured 3-arc problem-solving educational script using the specified AI provider
    with graceful multi-tier fallbacks.

    Args:
        topic (str): The subject matter to teach.
        visual_style (str): The aesthetic style for Nano Banana FLUX visual prompts.
        complexity (str): Target audience comprehension level.
        provider (str): 'groq', 'gemini', 'llama31', 'mistral', or 'ollama'.

    Returns:
        dict: The structured 3-arc pedagogical script in valid JSON format.
    """
    print(f"🧠 [Script Engine] Generating 3-Arc Problem Solving Script for: '{topic}' via {provider.upper()}...")

    system_prompt = PEDAGOGICAL_SYSTEM_PROMPT.replace("<inject_visual_style>", visual_style)
    system_prompt = system_prompt.replace("<inject_complexity>", complexity)
    user_prompt = (
        f"Write an elite 3-Arc Problem-Solving tutorial script explaining: '{topic}'.\n"
        f"Ensure strict 3-arc structure (Problem Hook -> Analogy Bridge -> Step-by-Step Resolution with 3-5 progressive steps), "
        f"vivid Dual-Speaker Dialogue (TEACHER & STUDENT), and hyper-detailed Nano Banana FLUX visual prompts for every step.\n"
        f"Return ONLY valid JSON matching the exact schema."
    )

    provider_clean = (provider or "groq").lower().strip()

    # Prioritize selected provider, cascade gracefully through alternates
    if provider_clean == "gemini":
        attempts = [("Gemini", _call_gemini_api), ("Groq", _call_groq_api), ("HuggingFace", _call_huggingface_api)]
    elif provider_clean == "llama31":
        attempts = [("HuggingFace", _call_huggingface_api), ("Groq", _call_groq_api), ("Gemini", _call_gemini_api)]
    elif provider_clean == "mistral":
        attempts = [("Mistral", _call_mistral_api), ("Groq", _call_groq_api), ("Gemini", _call_gemini_api)]
    elif provider_clean == "ollama":
        attempts = [("Ollama", _call_ollama_api), ("Groq", _call_groq_api), ("Gemini", _call_gemini_api)]
    else:  # default groq
        attempts = [("Groq", _call_groq_api), ("Gemini", _call_gemini_api), ("HuggingFace", _call_huggingface_api)]

    for prov_name, call_fn in attempts:
        try:
            print(f"🧠 [Script Engine] Contacting {prov_name} API...")
            raw_response = call_fn(user_prompt, system_prompt)
            if raw_response:
                cleaned_json = _clean_json_response(raw_response)
                script_data = json.loads(cleaned_json)

                # Validate essential 3-arc fields
                if isinstance(script_data, dict):
                    has_hook = "problem_hook" in script_data
                    has_analogy = "analogy_bridge" in script_data
                    has_steps = "solution_steps" in script_data or "steps" in script_data

                    if has_hook or has_analogy or has_steps:
                        # Normalize 'steps' key if model returned 'steps' instead of 'solution_steps'
                        if "steps" in script_data and "solution_steps" not in script_data:
                            script_data["solution_steps"] = script_data.pop("steps")

                        print(f"✨ [Script Engine] Successfully generated 3-arc script via {prov_name}!")
                        return script_data
        except Exception as e:
            print(f"⚠️ [Script Engine] {prov_name} generation failed: {e}")
            continue

    print("🛑 [Script Engine] All AI provider attempts exhausted. Using intelligent built-in generator.")
    return _get_fallback_script(topic, visual_style)


# ============================================================================
# LEGACY FORMAT CONVERTER
# ============================================================================

def pedagogical_to_steps(script: dict) -> list:
    """
    Converts the 3-arc pedagogical script dict into the legacy StepList format
    consumed by image_generator.py, voice_generator.py, and video_assembler.py.

    Each step dictionary contains:
        step_number, title, narration, image_prompt, motion_prompt,
        duration_seconds, components, teacher_line, student_line,
        arc_phase ('problem' | 'analogy' | 'solution'), arc_label, speaker

    Args:
        script (dict): The generated 3-arc script.

    Returns:
        list: A list of step dictionaries formatted for the downstream pipeline.
    """
    print("🔄 [Pedagogy] Converting 3-arc script to pipeline steps format...")

    steps = []
    current_step_index = 1

    # 1. Arc 1 - Problem Hook Step
    if "problem_hook" in script and isinstance(script["problem_hook"], dict):
        hook = script["problem_hook"]
        teacher_text = hook.get("teacher_line", "").strip()
        student_text = hook.get("student_line", "").strip()
        narration = f"{teacher_text} {student_text}".strip() or hook.get("hook_text", "")

        steps.append({
            "step_number": current_step_index,
            "title": hook.get("hook_text") or "The Core Problem & Dilemma",
            "narration": narration,
            "image_prompt": hook.get("visual_prompt", ""),
            "motion_prompt": hook.get("motion_hint", "slow dramatic zoom in"),
            "duration_seconds": hook.get("duration_seconds", 6),
            "components": hook.get("components", []),
            "teacher_line": teacher_text,
            "student_line": student_text,
            "arc_phase": "problem",
            "arc_label": "The Problem",
            "speaker": "Teacher"
        })
        current_step_index += 1

    # 2. Arc 2 - Analogy Bridge Step
    if "analogy_bridge" in script and isinstance(script["analogy_bridge"], dict):
        bridge = script["analogy_bridge"]
        teacher_text = bridge.get("teacher_line", "").strip()
        student_text = bridge.get("student_line", "").strip()
        narration = f"{teacher_text} {student_text}".strip() or bridge.get("analogy_text", "")

        steps.append({
            "step_number": current_step_index,
            "title": bridge.get("analogy_text") or "The Physical Analogy",
            "narration": narration,
            "image_prompt": bridge.get("visual_prompt", ""),
            "motion_prompt": bridge.get("motion_hint", "smooth orbital pan"),
            "duration_seconds": bridge.get("duration_seconds", 6),
            "components": bridge.get("components", []),
            "teacher_line": teacher_text,
            "student_line": student_text,
            "arc_phase": "analogy",
            "arc_label": "The Analogy",
            "speaker": "Teacher"
        })
        current_step_index += 1

    # 3. Arc 3 - Progressive Solution Steps
    solution_steps_list = script.get("solution_steps") or script.get("steps") or []
    if isinstance(solution_steps_list, list):
        sol_idx = 1
        for sol_step in solution_steps_list:
            if not isinstance(sol_step, dict):
                continue
            teacher_text = sol_step.get("teacher_line", "").strip()
            student_text = sol_step.get("student_line", "").strip()
            narration = f"{teacher_text} {student_text}".strip() or sol_step.get("title", "")

            steps.append({
                "step_number": current_step_index,
                "title": sol_step.get("title", f"Resolution Step {sol_idx}"),
                "narration": narration,
                "image_prompt": sol_step.get("visual_prompt", ""),
                "motion_prompt": sol_step.get("motion_hint", "camera tracking along flow"),
                "duration_seconds": sol_step.get("duration_seconds", 5),
                "components": sol_step.get("components", []),
                "teacher_line": teacher_text,
                "student_line": student_text,
                "arc_phase": "solution",
                "arc_label": f"Solution {sol_idx}",
                "speaker": "Teacher"
            })
            current_step_index += 1
            sol_idx += 1

    print(f"✅ [Pedagogy] Successfully converted into {len(steps)} pipeline steps with 3-arc metadata.")
    return steps


# ============================================================================
# MODULE ENTRY POINT (FOR DIRECT TESTING)
# ============================================================================

if __name__ == "__main__":
    print("🚀 [Pedagogy] Starting VisuAIze Pedagogy Engine Test...")

    test_topic = "The Human Heart"
    test_style = "classic"

    script_output = generate_pedagogical_script(test_topic, test_style, provider="groq")

    print("\n--- GENERATED JSON SCRIPT ---")
    print(json.dumps(script_output, indent=2))

    print("\n--- PIPELINE STEPS CONVERSION ---")
    legacy_steps = pedagogical_to_steps(script_output)
    print(json.dumps(legacy_steps, indent=2))
    print(f"\n✅ [Pedagogy] Test completed successfully with {len(legacy_steps)} steps.")
