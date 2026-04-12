import threading
import sounddevice as sd
import sys
from silero_tts import OfflineSileroTTS
import config
import time

class TTSEngine:
    def __init__(self):
        self.tts = OfflineSileroTTS(languages=["ru"], device="cpu", optimize=True)
        
    def speak(self, text):
        def _worker():
            audio = self.tts.synthesize(text, speaker=config.TTS_SPEAKER)
            if audio is not None and len(audio) > 0:
                for i in range(3):
                    sd.play(audio, samplerate=48000, blocking=True)
        threading.Thread(target=_worker, daemon=True).start()