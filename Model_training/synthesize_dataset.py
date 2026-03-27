import sounddevice as sd
import soundfile as sf
import os

COMMANDS = ["ПУСК", "СТОП", "ПАУЗА", "СБРОС", "ДАЛЕЕ", "НАЗАД", "ТРЕВОГА"]
DIR_NAMES = ["START", "STOP", "PAUSE", "RESET", "NEXT", "BACK", "DANGER"]
REPEATS_PER_PERSON = 20
SAMPLE_RATE = 22050
DURATION = 2.0

def record_command(command, dir,  index, person_id):
    print(f"Говорите: '{command}' ({index+1}/{REPEATS_PER_PERSON})")
    for i in range(3, 0, -1):
        print(i)
        sd.sleep(1000)
    
    print("ГОВОРИТЕ")
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()
    
    filename = f"Model_training/data/person_{person_id}/{dir}/{index:03d}.wav"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    sf.write(filename, recording, SAMPLE_RATE)
    print("OK\n")

person_id = input("Введите ID: ")
for i in range(len(COMMANDS)):
    for j in range(REPEATS_PER_PERSON):
        record_command(COMMANDS[i], DIR_NAMES[i], j, person_id)