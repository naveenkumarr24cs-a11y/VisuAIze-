"""
VisuAIze - Pedagogy Engine (NotebookLM-Style P→A→S Script Generator)
=====================================================================
Implements the exact 3-arc pedagogical structure used in Google NotebookLM:
  Arc 1 - PROBLEM HOOK: Vivid, relatable problem statement that grabs attention
  Arc 2 - ANALOGY BRIDGE: Real-world analogy that makes the concept instantly click
  Arc 3 - SOLUTION STEPS: Step-by-step clear resolution with visual descriptions

Also generates DUAL-SPEAKER DIALOGUE segments:
  TEACHER: Confident, warm, authoritative voice
  STUDENT: Curious, energetic, asks questions voice

This is the core intelligence that makes VisuAIze match NotebookLM quality.
"""

import os
import json
import re
import traceback

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
# SYSTEM PROMPT DEFINITION
# ============================================================================

PEDAGOGICAL_SYSTEM_PROMPT = """You are an elite AI educational scriptwriter, specializing in the NotebookLM-style "Problem -> Analogy -> Solution" (P->A->S) framework. Your goal is to write a highly engaging, dual-speaker educational script that makes complex topics instantly understandable.

The output must follow this exact 3-arc structure:
1. PROBLEM HOOK: A vivid, relatable problem statement that grabs attention immediately. It should establish "why should I care?"
2. ANALOGY BRIDGE: A brilliant real-world analogy that makes the core concept instantly click. (The "aha!" moment).
3. SOLUTION STEPS: A step-by-step clear resolution breaking down the concept, complete with vivid visual descriptions for an AI video generator.

The dialogue features TWO speakers:
- TEACHER: Confident, warm, authoritative, guiding the explanation.
- STUDENT: Curious, energetic, relatable, asking the questions the audience is thinking.

You MUST respond with valid JSON ONLY. No markdown wrappers, no introductory text, no conversational filler. Return exactly a JSON object matching this schema:

{
  "title": "A catchy, engaging title",
  "visual_style": "<inject_visual_style>",
  "problem_hook": {
    "hook_text": "The gripping opening line or problem statement",
    "teacher_line": "Teacher: The initial hook explanation.",
    "student_line": "Student: Wait, so you mean [relatable struggle]?",
    "visual_prompt": "Detailed AI image prompt illustrating the problem hook scene.",
    "motion_hint": "Camera direction, e.g., 'slow zoom in, dramatic lighting'",
    "duration_seconds": 6
  },
  "analogy_bridge": {
    "analogy_text": "The core analogy sentence",
    "teacher_line": "Teacher: Think of it like [the analogy].",
    "student_line": "Student: Oh! So it's basically just like [confirming the analogy]?",
    "visual_prompt": "Detailed AI image prompt showing the analogy vividly.",
    "motion_hint": "Camera direction, e.g., 'pan left, dynamic motion'",
    "duration_seconds": 6
  },
  "solution_steps": [
    {
      "step_number": 1,
      "title": "Step 1 Title",
      "teacher_line": "Teacher: First, we [action].",
      "student_line": "Student: Makes sense! And then what?",
      "visual_prompt": "Detailed AI image prompt for this specific step.",
      "motion_hint": "Camera direction",
      "duration_seconds": 5,
      "components": [{"name": "item", "desc": "description", "x": 0.5, "y": 0.5}]
    },
    {
      "step_number": 2,
      "title": "Step 2 Title",
      "teacher_line": "Teacher: Next, [action].",
      "student_line": "Student: I see, so that prevents [issue]!",
      "visual_prompt": "Detailed AI image prompt for step 2.",
      "motion_hint": "Camera direction",
      "duration_seconds": 5,
      "components": [{"name": "item2", "desc": "description2", "x": 0.3, "y": 0.7}]
    }
    // Add 2-4 more steps as needed to fully explain the topic
  ],
  "quiz": {
    "question": "A concluding question to test the student's understanding?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "Why this option is correct."
  }
}

Ensure the visual_prompts are incredibly descriptive, noting lighting, style, composition, and core subjects. 
The complexity level of the explanation should target a: <inject_complexity>
"""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _clean_json_response(text: str) -> str:
    """Strips markdown formatting from LLM responses to ensure valid JSON."""
    text = text.strip()
    # Remove markdown code block wrappers if they exist
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
        
    return text.strip()

def _get_fallback_script(topic: str, visual_style: str) -> dict:
    """Provides a hardcoded fallback script in case all APIs fail or return invalid data."""
    return {
        "title": f"Understanding {topic}",
        "visual_style": visual_style,
        "problem_hook": {
            "hook_text": f"Have you ever struggled to understand {topic}? It can seem incredibly complex.",
            "teacher_line": f"Many people find {topic} confusing at first glance.",
            "student_line": "Yeah, it just looks like a massive jumble of information to me!",
            "visual_prompt": f"A confused person looking at a complex blackboard full of equations about {topic}, {visual_style} style",
            "motion_hint": "slow zoom in on the confused face, dramatic lighting",
            "duration_seconds": 6
        },
        "analogy_bridge": {
            "analogy_text": f"Think of {topic} like building a house with Lego blocks.",
            "teacher_line": "Think of it like building a house with Lego blocks. You start with a foundation.",
            "student_line": "Oh! So you just put the pieces together step by step?",
            "visual_prompt": f"A giant, glowing Lego house being built block by block to represent {topic}, {visual_style} style",
            "motion_hint": "pan right, dynamic motion showing construction",
            "duration_seconds": 6
        },
        "solution_steps": [
            {
                "step_number": 1,
                "title": "The Foundation",
                "teacher_line": "First, we lay down the core principles.",
                "student_line": "Makes sense! You need a strong base.",
                "visual_prompt": f"Laying the foundation of a structure representing {topic}, glowing blueprint lines, {visual_style} style",
                "motion_hint": "steady shot, glowing effects",
                "duration_seconds": 5,
                "components": [{"name": "foundation", "desc": "the base structure", "x": 0.5, "y": 0.8}]
            },
            {
                "step_number": 2,
                "title": "Building Up",
                "teacher_line": "Next, we add the details and connections.",
                "student_line": "I see, so that's where the real magic happens!",
                "visual_prompt": f"Adding walls and details to the structure, representing {topic}, {visual_style} style",
                "motion_hint": "slow zoom out to reveal the whole structure",
                "duration_seconds": 5,
                "components": [{"name": "walls", "desc": "the connected details", "x": 0.5, "y": 0.4}]
            }
        ],
        "quiz": {
            "question": f"What is the best analogy for understanding {topic}?",
            "options": ["Building with Legos", "Cooking a meal", "Driving a car", "Painting a picture"],
            "correct_index": 0,
            "explanation": "The Lego analogy perfectly captures the step-by-step assembly of concepts."
        }
    }

# ============================================================================
# API CALLERS
# ============================================================================

def _call_groq_api(prompt: str, system_prompt: str) -> str:
    """Calls the Groq API directly using requests."""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set.")
    
    if requests is None:
        raise ImportError("requests library is not installed, cannot call Groq REST API.")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    return data['choices'][0]['message']['content']

def _call_gemini_api(prompt: str, system_prompt: str) -> str:
    """Calls the Gemini API using the google-genai SDK."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    if not GOOGLE_GENAI_AVAILABLE or google_genai is None:
        raise ImportError("google-genai library is not installed. Run: pip install google-genai")

    client = google_genai.Client(api_key=api_key)
    full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{prompt}"

    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[full_prompt]
            )
            if response.text:
                return response.text
        except Exception:
            continue

    raise RuntimeError("All Gemini models failed.")


# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

def generate_pedagogical_script(topic: str, visual_style: str = 'classic', complexity: str = 'STUDENT') -> dict:
    """
    Generates a NotebookLM-style Problem->Analogy->Solution pedagogical script.
    
    Args:
        topic (str): The subject matter to teach.
        visual_style (str): The aesthetic style for image prompts (e.g., 'whiteboard', 'kawaii').
        complexity (str): The target audience comprehension level.
        
    Returns:
        dict: The structured pedagogical script in JSON format.
    """
    print(f"🧠 [Pedagogy] Generating P→A→S script for topic: '{topic}'...")
    
    # Inject variables into the system prompt
    system_prompt = PEDAGOGICAL_SYSTEM_PROMPT.replace("<inject_visual_style>", visual_style)
    system_prompt = system_prompt.replace("<inject_complexity>", complexity)
    
    user_prompt = f"Write a pedagogical P->A->S script explaining this topic: '{topic}'. Remember to return ONLY valid JSON."
    
    raw_response = ""
    script_data = None
    
    # Attempt 1: Groq (llama-3.3-70b-versatile)
    try:
        print("🧠 [Pedagogy] Attempting generation with Groq API (llama-3.3-70b-versatile)...")
        raw_response = _call_groq_api(user_prompt, system_prompt)
        cleaned_json = _clean_json_response(raw_response)
        script_data = json.loads(cleaned_json)
        print("✨ [Pedagogy] Successfully generated script via Groq!")
        return script_data
    except Exception as e:
        print(f"⚠️ [Pedagogy] Groq generation failed: {e}")
        
    # Attempt 2: Gemini
    if not script_data:
        try:
            print("🧠 [Pedagogy] Falling back to Gemini API...")
            raw_response = _call_gemini_api(user_prompt, system_prompt)
            cleaned_json = _clean_json_response(raw_response)
            script_data = json.loads(cleaned_json)
            print("✨ [Pedagogy] Successfully generated script via Gemini!")
            return script_data
        except Exception as e:
            print(f"⚠️ [Pedagogy] Gemini generation failed: {e}")
            
    # Attempt 3: Fallback Template
    if not script_data:
        print("🛑 [Pedagogy] All API attempts failed or APIs unavailable. Using hardcoded fallback script.")
        print("💡 [Pedagogy] Check your GROQ_API_KEY or GEMINI_API_KEY environment variables.")
        return _get_fallback_script(topic, visual_style)

# ============================================================================
# LEGACY FORMAT CONVERTER
# ============================================================================

def pedagogical_to_steps(script: dict) -> list:
    """
    Converts the new pedagogical script dict into the legacy StepList format 
    that ai_provider.py and video_assembler.py expect.
    
    Each step will have: 
        step_number, title, narration, image_prompt, motion_prompt, 
        duration_seconds, components, teacher_line, student_line
        
    Args:
        script (dict): The generated P->A->S script.
        
    Returns:
        list: A list of step dictionaries in legacy format.
    """
    print("🔄 [Pedagogy] Converting pedagogical script to legacy steps format...")
    
    steps = []
    current_step_index = 1
    
    # 1. Add Problem Hook Step
    if 'problem_hook' in script:
        hook = script['problem_hook']
        narration = f"{hook.get('teacher_line', '')} {hook.get('student_line', '')}".strip()
        
        steps.append({
            'step_number': current_step_index,
            'title': "The Problem",
            'narration': narration,
            'image_prompt': hook.get('visual_prompt', ''),
            'motion_prompt': hook.get('motion_hint', ''),
            'duration_seconds': hook.get('duration_seconds', 6),
            'components': [],
            'teacher_line': hook.get('teacher_line', ''),
            'student_line': hook.get('student_line', '')
        })
        current_step_index += 1
        
    # 2. Add Analogy Bridge Step
    if 'analogy_bridge' in script:
        bridge = script['analogy_bridge']
        narration = f"{bridge.get('teacher_line', '')} {bridge.get('student_line', '')}".strip()
        
        steps.append({
            'step_number': current_step_index,
            'title': "The Analogy",
            'narration': narration,
            'image_prompt': bridge.get('visual_prompt', ''),
            'motion_prompt': bridge.get('motion_hint', ''),
            'duration_seconds': bridge.get('duration_seconds', 6),
            'components': [],
            'teacher_line': bridge.get('teacher_line', ''),
            'student_line': bridge.get('student_line', '')
        })
        current_step_index += 1
        
    # 3. Add Solution Steps
    if 'solution_steps' in script:
        for sol_step in script['solution_steps']:
            narration = f"{sol_step.get('teacher_line', '')} {sol_step.get('student_line', '')}".strip()
            
            steps.append({
                'step_number': current_step_index,
                'title': sol_step.get('title', f"Step {current_step_index}"),
                'narration': narration,
                'image_prompt': sol_step.get('visual_prompt', ''),
                'motion_prompt': sol_step.get('motion_hint', ''),
                'duration_seconds': sol_step.get('duration_seconds', 5),
                'components': sol_step.get('components', []),
                'teacher_line': sol_step.get('teacher_line', ''),
                'student_line': sol_step.get('student_line', '')
            })
            current_step_index += 1
            
    print(f"✅ [Pedagogy] Successfully converted into {len(steps)} legacy steps.")
    return steps

# ============================================================================
# MODULE ENTRY POINT (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    # A simple test runner when executed directly
    print("🚀 [Pedagogy] Starting VisuAIze Pedagogy Engine Test...")
    
    test_topic = "Quantum Entanglement"
    test_style = "chalkboard diagram, highly detailed"
    
    script_output = generate_pedagogical_script(test_topic, test_style)
    
    print("\n--- GENERATED JSON SCRIPT ---")
    print(json.dumps(script_output, indent=2))
    
    print("\n--- LEGACY STEPS CONVERSION ---")
    legacy_steps = pedagogical_to_steps(script_output)
    print(json.dumps(legacy_steps, indent=2))
    print("✅ [Pedagogy] Test completed.")
