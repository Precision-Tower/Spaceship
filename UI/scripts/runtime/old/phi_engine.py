import time
from pathlib import Path
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:
    AutoModelForCausalLM = None
    AutoTokenizer = None

def run_phi_inference(prompt: str, model_path: Path, max_new_tokens: int = 512):
    """
    Executes local inference using the Phi-3 model hub.
    Note: In the current CLI-based architecture, this will load the model into 
    memory on every call, which may take significant time (5-10s+).
    """
    if not AutoModelForCausalLM or not model_path.exists():
        return None
        
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path), 
        local_files_only=True, 
        low_cpu_mem_usage=True
    )
    
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
