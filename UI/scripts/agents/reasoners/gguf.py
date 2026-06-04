# agents/reasoners/gguf.py
import os
from UI.scriptshlib import Path
from UI.scriptsma_cpp import Llama

class CodeReasoner:
    def __init__(self, model_path: str):
        self.model_path = str(Path(model_path).expanduser())
        self.llm = None

    def load(self):
        if self.llm is not None: return True
        try:
            print("[*] Loading GGUF model into System RAM...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_gpu_layers=0,
                n_threads=max(1, (os.cpu_count() or 2) - 1),
                verbose=False
            )
            print("[+] GGUF engine online.")
            return True
        except Exception as e:
            print(f"[!] Critical load failure: {e}")
            return False

    def generate(self, system_context, user_prompt, max_new_tokens=512):
        if not self.load(): return "Engine offline."
        
        full_text = f"{system_context}\n\nUser: {user_prompt}\nAssistant:"
        output = self.llm(
            full_text,
            max_tokens=max_new_tokens,
            temperature=0.2,
            repeat_penalty=1.15,
            stop=["\nweebo>", "\nUser:", "\nUSER:", "\nHuman:"]
        )
        return output["choices"][0]["text"].strip()