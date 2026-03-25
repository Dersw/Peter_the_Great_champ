import torch
import numpy as np
import librosa
import pickle
from collections import deque
import threading
import time
from datetime import datetime
import torch
import torch.nn as nn
import sounddevice as sd

# ==========================================
# 1. КОНФИГУРАЦИЯ
# ==========================================
MODEL_PATH = r"C:\Users\User\Desktop\penis_of_Peter_the_Great\Model_training\model_pytorch.pt"
SCALER_PATH = r"C:\Users\User\Desktop\penis_of_Peter_the_Great\Model_training\scaler.pkl"
SAMPLE_RATE = 22050
BUFFER_DURATION = 3      
STEP_DURATION = 0.5
CONFIDENCE_THRESHOLD = 0.80
DEBOUNCE_SECONDS = 3

COMMANDS = ['назад', 'тревога', 'далее', 'пауза', 'сброс', 'пуск', 'стоп']

class audio_model(nn.Module):
    def __init__(self, input_features=162, num_classes=7):
        super(audio_model, self).__init__()
        
        self.conv_layers = nn.Sequential(
            # Блок 1
            nn.Conv1d(1, 32, kernel_size=3, padding=1),  # (N, 32, 162)
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),  # (N, 32, 81)
            nn.Dropout(0.1),
            
            # Блок 2
            nn.Conv1d(32, 64, kernel_size=3, padding=1),  # (N, 64, 81)
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),  # (N, 64, 40)
            nn.Dropout(0.1),
            
            # Блок 3
            nn.Conv1d(64, 128, kernel_size=3, padding=1),  # (N, 128, 40)
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.MaxPool1d(2),  # (N, 128, 20)
            nn.Dropout(0.1),
        )
        
        # После 3 MaxPool(2): 162 // 8 = 20
        self.flattened_size = 128 * 20
        
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(self.flattened_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        x = x.permute(0, 2, 1)
        x = self.conv_layers(x)
        x = self.classifier(x)
        return x

model = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
model.eval()

with open(SCALER_PATH, 'rb') as f:
    scaler = pickle.load(f)


def noise(data):
    noise_amp = 0.01 * np.random.uniform() * np.amax(data)
    data = data + noise_amp * np.random.normal(size=data.shape[0])
    return data

def stretch(data, rate=0.8):
    return librosa.effects.time_stretch(data, rate=rate)

def pitch(data, sampling_rate, pitch_factor=0.7):
    return librosa.effects.pitch_shift(data, sr=sampling_rate, n_steps=pitch_factor)


def extract_features(data, sr):
    result = np.array([])
    
    # ZCR (1 признак)
    zcr = np.mean(librosa.feature.zero_crossing_rate(y=data).T, axis=0)
    result = np.hstack((result, zcr))
    
    # Chroma_stft (12 признаков)
    stft = np.abs(librosa.stft(data))
    chroma_stft = np.mean(librosa.feature.chroma_stft(S=stft, sr=sr).T, axis=0)
    result = np.hstack((result, chroma_stft))
    
    # MFCC (20 признаков по умолчанию)
    mfcc = np.mean(librosa.feature.mfcc(y=data, sr=sr).T, axis=0)
    result = np.hstack((result, mfcc))
    
    # RMS (1 признак)
    rms = np.mean(librosa.feature.rms(y=data).T, axis=0)
    result = np.hstack((result, rms))
    
    # MelSpectrogram (128 признаков по умолчанию)
    mel = np.mean(librosa.feature.melspectrogram(y=data, sr=sr).T, axis=0)
    result = np.hstack((result, mel))
    
    return result

def get_features_for_inference(audio_data, sr):
    target_samples = int(SAMPLE_RATE * BUFFER_DURATION)
    if len(audio_data) < target_samples:
        audio_data = np.pad(audio_data, (0, target_samples - len(audio_data)))
    else:
        audio_data = audio_data[:target_samples]
    features = extract_features(audio_data, sr)
    
    features = scaler.transform([features])[0]
    
    return features.reshape(-1, 1).astype(np.float32)

class AudioBuffer:
    def __init__(self, duration=2.5, sample_rate=22050):
        self.sample_rate = sample_rate
        self.max_samples = int(duration * sample_rate)
        self.buffer = deque(maxlen=self.max_samples)
        self.lock = threading.Lock()
    
    def add(self, samples):
        with self.lock:
            self.buffer.extend(samples)
    
    def get_last_buffer(self):
        with self.lock:
            return np.array(self.buffer, dtype=np.float32)
    
    def is_ready(self):
        with self.lock:
            return len(self.buffer) >= self.max_samples


def audio_recorder_thread(audio_buffer):
    
    def callback(indata, frames, time_info, status):
        if status:
            print(f" {status}")
        audio_buffer.add(indata[:, 0].copy())
    
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=int(SAMPLE_RATE * 0.05),
        callback=callback
    ):
        while True:
            time.sleep(0.1)

last_command = None
last_command_time = 0

def inference_thread(audio_buffer):
    global last_command, last_command_time
    
    while True:
        if audio_buffer.is_ready():
            audio_data = audio_buffer.get_last_buffer()
            
            # Проверка энергии (чтобы не распознавать тишину)
            energy = np.sqrt(np.mean(audio_data**2))
            if energy < 0.01:  # Порог тишины
                time.sleep(STEP_DURATION)
                continue
            
            # Извлечение признаков
            features = get_features_for_inference(audio_data, SAMPLE_RATE)
            input_tensor = torch.FloatTensor(features).unsqueeze(0)
            
            # Предсказание
            with torch.no_grad():
                output = model(input_tensor)
                probabilities = torch.softmax(output, dim=1)[0]
                confidence, predicted = torch.max(probabilities, 0)
            
            confidence = confidence.item()
            command_idx = predicted.item()
            command_name = COMMANDS[command_idx]
            
            # Проверка порога
            current_time = time.time()
            if confidence >= CONFIDENCE_THRESHOLD:
                if command_name != last_command or (current_time - last_command_time) > DEBOUNCE_SECONDS:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"\n[{timestamp}] послана команда {command_name.upper()} (точность: {confidence:.2%})")
                    last_command = command_name
                    last_command_time = current_time
            else:
                if last_command and (current_time - last_command_time) > 1.0:
                    last_command = None
        
        time.sleep(STEP_DURATION)

# ==========================================
# 8. ЗАПУСК
# ==========================================
if __name__ == "__main__":
        
    audio_buffer = AudioBuffer(duration=BUFFER_DURATION, sample_rate=SAMPLE_RATE)
    
    recorder = threading.Thread(target=audio_recorder_thread, args=(audio_buffer,), daemon=True)
    analyzer = threading.Thread(target=inference_thread, args=(audio_buffer,), daemon=True)
    
    recorder.start()
    time.sleep(0.5)
    analyzer.start()
    
    while True:
        time.sleep(1)