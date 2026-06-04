from Spaceship.Models.Online.gemini_client import get_client, get_model_name
from runtime.phi_engine import run_phi_inference
from runtime.paths import DASHBOARD_ROOT
import datetime

PHI_MODEL_PATH = DASHBOARD_ROOT / "Models" / "Phi-3-mini-4k-instruct"

def request_analysis(purpose, context):
    """
    Orchestrates analysis using the Local Hub (Phi-3) first.
    Escalates to the Teacher (Gemini) only when requested or necessary.
    """
    # Hub-First Strategy
    prompt = (
        f"PURPOSE: {purpose}\n"
        f"CONTEXT: {context}\n"
        f"BOUNDARY: Local Hub Analysis. Mutation prohibited. No shell execution.\n"
        f"INSTRUCTION: If context is too dense or specialized, include [TEACHER_REQUIRED] in response."
    )
    
    hub_response = run_phi_inference(prompt, PHI_MODEL_PATH)
    
    # If local hub succeeds and doesn't request escalation
    if hub_response and "[TEACHER_REQUIRED]" not in hub_response:
        return {
            "model": "phi-3-local-hub",
            "prompt_summary": purpose,
            "response_text": hub_response,
            "authority": "hub_analysis",
            "mutation_allowed": False,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    # Teacher Fallback (Gemini)
    client = get_client()
    if not client:
        return {"status": "Hub limit reached, Teacher (Gemini) unavailable", "authority": "none"}

    model_name = get_model_name()
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        # Safely extract text; safety filters can block the .text attribute
        try:
            text_payload = response.text
        except ValueError:
            text_payload = "[REDACTED: Response blocked by safety filters or safety settings too restrictive.]"
            if hasattr(response, 'prompt_feedback'):
                text_payload += f"\nFeedback: {response.prompt_feedback}"

        return {
            "model": model_name,
            "prompt_summary": purpose,
            "response_text": text_payload,
            "authority": "candidate_only",
            "mutation_allowed": False,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error_detail": str(e),
            "authority": "none",
            "mutation_allowed": False,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }