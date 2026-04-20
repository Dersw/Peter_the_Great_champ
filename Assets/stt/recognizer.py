import json
import time
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import config
from utils.logger import log

class STTEngine:
    def __init__(self, on_command):
        self.on_command = on_command
        self.model = Model(config.MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, config.SAMPLE_RATE)
        self.recognizer.SetWords(False)
        
        self.stream = None
        self.speech_frames = 0
        self.silence_frames = 0
        self.last_partial = ""
        self._last_cmd = ""
        self._last_cmd_time = 0

        log.info(f"STT модуль инициализирован. Команд загружено: {len(config.COMMANDS)}")

    def _audio_callback(self, indata, frames, time_info, status):
        audio_chunk = indata[:, 0]
        audio_int16 = (audio_chunk * 32767).astype(np.int16)
        
        energy = np.sqrt(np.mean(audio_chunk**2)) * 32767
        is_speech = energy > config.ENERGY_THRESHOLD

        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1

        if self.recognizer.AcceptWaveform(audio_int16.tobytes()):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                log.info(f"Финальное распознавание: '{text}'")
                self._check(text)
        else:
            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get("partial", "").strip()
            if partial_text and partial_text != self.last_partial:
                self.last_partial = partial_text
                for cmd_word in config.COMMANDS:
                    if cmd_word in partial_text.lower():
                        log.cmd(f"Ранний тригер: '{partial_text}' -> {config.COMMANDS[cmd_word]}")
                        self._trigger(config.COMMANDS[cmd_word])

        if not is_speech and self.speech_frames > 0:
            if (self.silence_frames * 30 / 1000) > config.COMMAND_TIMEOUT:
                result = json.loads(self.recognizer.FinalResult())
                text = result.get("text", "").strip()
                if text:
                    self._check(text)
                self.speech_frames = 0
                self.silence_frames = 0
                self.last_partial = ""
                self.recognizer.Reset()

    def _check(self, text):
        for key, cmd in config.COMMANDS.items():
            if key in text.lower():
                log.cmd(f"Команда потверждена: '{key}' -> {cmd}")
                self._trigger(cmd)
                return

    def _trigger(self, command):
        now = time.time()
        if command == self._last_cmd and (now - self._last_cmd_time) < config.DEBOUNCE_INTERVAL:
            return
        self._last_cmd = command
        self._last_cmd_time = now
        self.on_command(command)

    def start(self):
        self.stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            blocksize=int(config.SAMPLE_RATE * 0.03),
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            log.info("STT поток остановлен пользователем")
            self.stream.stop()
            self.stream.close()