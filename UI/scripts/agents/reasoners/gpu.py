import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
)


class CodeReasoner:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.pipeline = None

    def load(self):
        if self.model is not None:
            return True

        print("[*] Initializing GPU-Accelerated Reasoner...")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            quantization_config=bnb_config,
            device_map="auto",
        )

        self.pipeline = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device_map="auto",
        )

        return True

    def generate(self, system_context, user_prompt, max_new_tokens=512):
        self.load()

        full_prompt = f"{system_context}\n\nUser: {user_prompt}\nAssistant:"
        response = self.pipeline(full_prompt, max_new_tokens=max_new_tokens)

        return response[0]["generated_text"].replace(full_prompt, "").strip()