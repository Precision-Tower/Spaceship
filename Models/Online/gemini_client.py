import os
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def get_model_name():
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

def list_available_models():
    client = get_client()
    if not client:
        return []
    # List models to see what the API key actually has access to
    return [m.name for m in client.models.list()]