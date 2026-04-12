import json
import time
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

SAMPLE_RATE = 16000
COMMAND_TIMEOUT = 0.8
ENERGY_THRESHOLD = 300

COMMANDS = {
    "стоп": "СТОП",
    "пуск": "ПУСК", 
    "запуск": "ПУСК",
    "дальше": "ДАЛЬШЕ",
    "далее": "ДАЛЬШЕ"
}

class IndustrialVoiceControl:
    def __init__(self, model_path="model"):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.recognizer.SetWords(False)
        
        self.stream = None
        self.speech_frames = 0
        self.silence_frames = 0
        
    def audio_callback(self, indata, frames, time_info, status):
        audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
        
        # VAD по энергии
        energy = np.sqrt(np.mean(indata[:, 0]**2)) * 32767
        is_speech = energy > ENERGY_THRESHOLD
        
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1
        
        if self.recognizer.AcceptWaveform(audio_int16.tobytes()):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "")
            if text:
                self.check_command(text)
        else:
            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get("partial", "")
            if partial_text:
                for cmd_word in COMMANDS.keys():
                    if cmd_word in partial_text.lower():
                        self.execute_command(COMMANDS[cmd_word])
                        return
        
        if not is_speech and self.speech_frames > 0:
            if self.silence_frames * 30 / 1000 > COMMAND_TIMEOUT:
                result = json.loads(self.recognizer.FinalResult())
                text = result.get("text", "")
                if text:
                    self.check_command(text)
                self.speech_frames = 0
    
    def check_command(self, text):
        text_lower = text.lower().strip()
        for key, cmd in COMMANDS.items():
            if key in text_lower:
                self.execute_command(cmd)
                return True
        return False
    
    def execute_command(self, command):
        print(f"зарегистрирована команда \"{command}\"")
    
    def start(self):
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=int(SAMPLE_RATE * 0.03),
            dtype='float32',
            callback=self.audio_callback
        )
        self.stream.start()
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stream.stop()
            self.stream.close()

if __name__ == "__main__":
    controller = IndustrialVoiceControl()
    controller.start()