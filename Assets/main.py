import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from cli import select_speaker
from stt.recognizer import STTEngine
from tts.synthesizer import TTSEngine

def main():
    config.TTS_SPEAKER = select_speaker()
    print(f"✅ Выбран голос: {config.TTS_SPEAKER}")

    print("\n⏳ Запуск контроллера...")
    tts = TTSEngine()
    
    def on_command(command):
        print(f"Команда: {command.lower()}")
        tts.speak(config.TTS_PHRASES.get(command, "Команда принята."))

    stt = STTEngine(on_command)
    stt.start()

if __name__ == "__main__":
    main()