#!/usr/bin/env python3
import json
import sys
import queue
import sounddevice as sd
import vosk
from lib import Path

# Package Imports
from UI.scripts.agents.core import WeeboAgent, CaliBridge, WeeboMemory, PathResolver
from UI.scripts.listeners.controller import WeeboController
from UI.scripts.reasoners.gguf import CodeReasoner as Reasoner

# Constants
CLR_CYAN = "\033[96m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_RESET = "\033[0m"
CLR_RED = "\033[91m"
CLR_BOLD = "\033[1m"

class WeeboWakeLoop:
    def __init__(self):
        # 1. Setup Core Components
        self.resolver = PathResolver()
        self.reasoner = Reasoner(self.resolver.get_model_path())
        self.bridge = CaliBridge(self.resolver)
        self.memory = WeeboMemory(str(Path(__file__).resolve().parent.parent / "persistence"))
        self.agent = WeeboAgent(self.reasoner, self.bridge, self.memory)
        
        # 2. Controller & Interrupt Logic
        self.interrupt_flag_path = Path(__file__).resolve().parent / "interrupt.flag"
        self.controller = WeeboController(self.agent, self.bridge, self.interrupt_flag_path)
        
        # 3. Audio Stream Setup
        self.device_info = sd.query_devices(0, 'input')
        self.native_samplerate = int(self.device_info['default_samplerate'])
        self.audio_queue = queue.Queue()
        
        # 4. Initialize Recognition
        print(f"{CLR_CYAN}[*] Loading Vosk Wake Word Model...{CLR_RESET}")
        self.vosk_model = vosk.Model(lang="en-us")
        self.rec_wake = vosk.KaldiRecognizer(self.vosk_model, self.native_samplerate, '["weebo", "hello", "computer", "[unk]"]')
        self.rec_cmd = vosk.KaldiRecognizer(self.vosk_model, self.native_samplerate)
        
        self.state = "WAITING_FOR_WAKE"

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"{CLR_RED}[Stream Status Error] {status}{CLR_RESET}", file=sys.stderr)
        self.audio_queue.put(bytes(indata))

    def run(self):
        print(f"\n{CLR_GREEN}{CLR_BOLD}=== WEEBO VOICE WAKE DAEMON ONLINE ==={CLR_RESET}")
        self.reasoner.load()
        
        if self.interrupt_flag_path.exists():
            self.interrupt_flag_path.unlink()

        try:
            with sd.InputStream(device=0, samplerate=self.native_samplerate, blocksize=1024, dtype='int16', channels=1, callback=self.audio_callback):
                print(f"Listening for wake word: {CLR_BOLD}'Weebo'{CLR_RESET}...\n")
                
                while True:
                    try:
                        data = self.audio_queue.get(timeout=0.01)
                    except queue.Empty:
                        continue

                    # CHECK FOR INTERRUPT / WAKE WHILE BUSY
                    if self.controller.is_busy():
                        if self.rec_wake.AcceptWaveform(data):
                            text = json.loads(self.rec_wake.Result()).get("text", "")
                            if any(w in text for w in ["weebo", "wee", "bo", "hello", "computer"]):
                                self.controller.trigger_interrupt()
                                self.state = "LISTENING_FOR_COMMAND"
                        continue

                    # STATE MACHINE
                    if self.state == "WAITING_FOR_WAKE":
                        if self.rec_wake.AcceptWaveform(data):
                            text = json.loads(self.rec_wake.Result()).get("text", "")
                            if any(w in text for w in ["weebo", "wee", "bo", "hello", "computer"]):
                                self.controller.trigger_wake()
                                self.state = "LISTENING_FOR_COMMAND"
                    
                    elif self.state == "LISTENING_FOR_COMMAND":
                        if self.rec_cmd.AcceptWaveform(data):
                            command = json.loads(self.rec_cmd.Result()).get("text", "").strip()
                            if command:
                                status = self.controller.execute_command(command)
                                if status == "EXIT":
                                    self.state = "WAITING_FOR_WAKE"
                                else:
                                    self.state = "BUSY" # Controller handles thread
                            else:
                                self.state = "WAITING_FOR_WAKE"

                    # CLEANUP FINISHED WORK
                    if self.state == "BUSY":
                        report = self.controller.check_worker_status()
                        if report:
                            self.state = "WAITING_FOR_WAKE"
                            if report['result']: print(f"\n{CLR_GREEN}WEEBO:{CLR_RESET} {report['result']}")

        except KeyboardInterrupt:
            print(f"\n{CLR_CYAN}[*] Terminated.{CLR_RESET}")

if __name__ == "__main__":
    WeeboWakeLoop().run()