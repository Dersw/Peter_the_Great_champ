# tts/synthesizer.py
import threading
import sounddevice as sd
import numpy as np
import wave
import io
import traceback
from silero_tts import OfflineSileroTTS
import config

class TTSEngine:
    SAMPLE_RATES = {"ru": 48000, "en": 24000}
    
    def __init__(self):
        print("Инициализация моделей Silero TTS...")
        try:
            self.tts_ru = OfflineSileroTTS(languages=["ru"], device="cpu", optimize=True)
            self.tts_en = OfflineSileroTTS(languages=["en"], device="cpu", optimize=True)
            print(f"Модели загружены")
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            traceback.print_exc()
            raise
        self.volume = 1.0
        self.speed = 1.0
        
    def _get_speaker(self, lang: str, requested_speaker: str = None, fallback_speaker: str = None) -> str:
        if lang == "en":
            return "en_0"
        
        if requested_speaker and requested_speaker.strip():
            return requested_speaker.strip()
        
        if fallback_speaker and fallback_speaker.strip():
            return fallback_speaker.strip()
        
        return getattr(config, "TTS_SPEAKER", "xenia")

    def _synthesize_raw(self, text: str, speaker: str = None, lang: str = "ru", *, fallback_speaker: str = None) -> tuple[np.ndarray, int]:
        text = text.lower().replace("я", "йа") + "..."
        spk = self._get_speaker(lang, speaker, fallback_speaker)
        engine = self.tts_en if lang == "en" else self.tts_ru
        sr = self.SAMPLE_RATES.get(lang, 48000)
        
        print(f"TTS: lang={lang} → спикер='{spk}', sr={sr}, текст='{text[:40]}...'")
        
        try:
            audio = engine.synthesize(text, speaker=spk)
            print(f"Озвучивание:")
        except Exception as e:
            print(f"Ошибка синтеза: {e}")
            traceback.print_exc()
            raise
            
        if audio is None or len(audio) == 0:
            raise ValueError("Пустой ввод!")
            
        if hasattr(audio, "cpu"): audio = audio.cpu().numpy()
        elif not isinstance(audio, np.ndarray): audio = np.array(audio)
        if audio.dtype in (np.float32, np.float64): audio = (audio * 32767).astype(np.int16)
        elif audio.dtype != np.int16: audio = audio.astype(np.int16)
        
        return audio, sr

    def _apply_effects(self, audio: np.ndarray, volume: float = None, speed: float = None) -> np.ndarray:
        vol = volume if volume is not None else self.volume
        spd = speed if speed is not None else self.speed
        if vol != 1.0: audio = (audio.astype(np.float32) * vol).astype(np.int16)
        if spd != 1.0:
            new_len = int(len(audio) / spd)
            if new_len > 0:
                indices = np.linspace(0, len(audio) - 1, new_len).astype(int)
                audio = audio[indices]
        return audio

    def speak(self, text: str, speaker: str = None, volume: float = None, speed: float = None, lang: str = "ru", fallback_speaker: str = None):
        print(f" speak(): lang={lang}, speaker={speaker}, fallback={fallback_speaker}")
        try:
            audio, sr = self._synthesize_raw(text, speaker, lang, fallback_speaker=fallback_speaker)
            audio = self._apply_effects(audio, volume, speed)
            print(f"Аудио готово: {len(audio)} сэмплов, sr={sr}")
        except Exception as e:
            print(f"❌ Ошибка в speak(): {e}")
            traceback.print_exc()
            return
        
        def _worker():
            try:
                for i in range(3):
                    print(f"Проигрывание #{i+1} (sr={sr})...")
                    sd.play(audio, samplerate=sr, blocking=True)
            except Exception as e:
                print(f"Ошибка воспроизведения: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def generate_to_bytes(self, text: str, speaker: str = None, volume: float = None, speed: float = None, lang: str = "ru", fallback_speaker: str = None) -> bytes:
        audio, sr = self._synthesize_raw(text, speaker, lang, fallback_speaker=fallback_speaker)
        audio = self._apply_effects(audio, volume, speed)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()