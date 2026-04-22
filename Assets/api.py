import sys
import os
import json
import time
import tempfile
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from tts.synthesizer import TTSEngine
from vosk import Model, KaldiRecognizer

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("api")

# Глобальное состояние
tts_engine: Optional[TTSEngine] = None
stt_model = None
is_tts_playing = False
tts_end_time = 0.0

class AppState:
    def __init__(self):
        self.current_speaker = getattr(config, "TTS_SPEAKER", "xenia")
        self.current_language = "ru"
        self.available_speakers = getattr(config, "AVAILABLE_SPEAKERS", ["xenia", "kseniya", "aidar", "baya"])
        self.supported_tts_languages = ["ru", "en"]

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_engine, stt_model
    logger.info("Инициализация API...")
    os.makedirs("temp", exist_ok=True)
    
    tts_engine = TTSEngine()
    stt_model = Model(getattr(config, "MODEL_PATH", "model_pytorch.pt"))
    
    logger.info(f"Запущено")
    yield
    logger.info("API остановлен")

app = FastAPI(title="Peter Voice API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SpeakRequest(BaseModel):
    text: str = "Вас приветствует голосовой помощник"
    command_key: Optional[str] = None
    volume: Optional[float] = 1
    speed: Optional[float] = 1

@app.get("/tts/status")
async def tts_status():
    return {
        "is_playing": is_tts_playing,
        "tts_end_time": tts_end_time
    }

# WebSocket
@app.websocket("/ws/stt")
async def websocket_stt(ws: WebSocket):
    global is_tts_playing, tts_end_time
    await ws.accept()
    recognizer = KaldiRecognizer(stt_model, 16000)
    recognizer.SetWords(False)
    
    prev_lang = state.current_language
    state.current_language = "ru"
    logger.info("WebSocket")
    
    try:
        while True:
            chunk = await ws.receive_bytes()
            
            # Блокировка: если TTS играет ИЛИ прошло менее 10 сек после окончания
            if is_tts_playing or (time.time() - tts_end_time) < 10.0:
                continue
                
            if len(chunk) % 2 != 0:
                continue
                
            if recognizer.AcceptWaveform(chunk):
                res = json.loads(recognizer.Result())
                raw_text = res.get("text", "").strip().lower()
                
                matched_cmd = next((cmd for key, cmd in config.COMMANDS.items() if key in raw_text), None)
                
                if matched_cmd:
                    phrase = config.TTS_PHRASES.get(matched_cmd, "Команда принята.")
                    logger.info(f"Команда '{matched_cmd}' → '{phrase}'")
                    
                    if tts_engine:
                        try:
                            is_tts_playing = True
                            tts_engine.speak(
                                phrase,
                                speaker=state.current_speaker,
                                lang=state.current_language,
                                volume=None,
                                speed=None
                            )
                            logger.info("TTS запущен")
                        except Exception as e:
                            logger.error(f"Ошибка TTS: {e}", exc_info=True)
                        finally:
                            is_tts_playing = False
                            tts_end_time = time.time()
                    
                    await ws.send_json({
                        "type": "final", "text": raw_text, "command": matched_cmd,
                        "phrase": phrase, "matched": True
                    })
                else:
                    await ws.send_json({"type": "final", "text": raw_text, "matched": bool(raw_text)})
            else:
                res = json.loads(recognizer.PartialResult())
                await ws.send_json({"type": "partial", "text": res.get("partial", "")})
                
    except Exception as e:
        logger.error(f"STT WebSocket ошибка: {e}")
    finally:
        state.current_language = prev_lang

# TTS Воспроизведение
@app.post("/speak")
async def speak_endpoint(req: SpeakRequest, bg_tasks: BackgroundTasks):
    global is_tts_playing, tts_end_time
    if not tts_engine:
        raise HTTPException(503, "TTS engine not ready")
        
    phrase = config.TTS_PHRASES.get(req.command_key, req.text) if req.command_key else req.text
    
    def _run_tts():
        global is_tts_playing, tts_end_time
        try:
            is_tts_playing = True
            tts_engine.speak(
                phrase,
                speaker=state.current_speaker,
                lang=state.current_language,
                volume=req.volume,
                speed=req.speed
            )
            time.sleep(1.0)
        except Exception as e:
            logger.error(f"Ошибка TTS: {e}", exc_info=True)
        finally:
            is_tts_playing = False
            tts_end_time = time.time()
            
    bg_tasks.add_task(_run_tts)
    return {"status": "success", "phrase": phrase}

# Скачать файл
@app.post("/tts/download")
async def tts_download(req: SpeakRequest, bg_tasks: BackgroundTasks):
    if not tts_engine:
        raise HTTPException(503, "TTS engine not ready")
    try:
        os.makedirs("temp", exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir="temp")
        audio_bytes = tts_engine.generate_to_bytes(
            req.text,
            speaker=state.current_speaker,
            lang=state.current_language,
            volume=req.volume,
            speed=req.speed
        )
        with open(tmp.name, "wb") as f:
            f.write(audio_bytes)
        bg_tasks.add_task(os.remove, tmp.name)
        return FileResponse(tmp.name, media_type="audio/wav", filename="tts.wav")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(500, f"Ошибка генерации: {e}")

# Настройки
@app.get("/settings")
async def get_settings():
    speaker = "en_0" if state.current_language == "en" else state.current_speaker
    return {
        "speaker": speaker,
        "language": state.current_language,
        "available_speakers": state.available_speakers,
        "supported_languages": state.supported_tts_languages,
        "tts_playing": is_tts_playing,
        "tts_end_time": tts_end_time
    }

@app.post("/settings")
async def update_settings(
    speaker: str = Query(None),
    language: str = Query(None)
):
    try:
        if language and language.strip() and language in state.supported_tts_languages:
            state.current_language = language.strip()
            if state.current_language == "en":
                state.current_speaker = "en_0"
            elif speaker and speaker.strip() and speaker in state.available_speakers:
                state.current_speaker = speaker.strip()
        elif speaker and speaker.strip() and state.current_language == "ru" and speaker in state.available_speakers:
            state.current_speaker = speaker.strip()
        return await get_settings()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return await get_settings()

# Веб-интерфейс
@app.get("/", response_class=HTMLResponse)
async def ui():
    API_URL = "http://127.0.0.1:8080"
    speakers = getattr(config, "AVAILABLE_SPEAKERS", ["xenia", "kseniya", "aidar", "baya"])
    speakers_html = "".join(f'<option value="{s}">{s}</option>' for s in speakers)
    languages_html = "".join(f'<option value="{lng}">{lng.upper()}</option>' for lng in ["ru", "en"])

    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Peter Voice</title>
<style>
    body{font-family:system-ui,sans-serif;max-width:700px;margin:30px auto;padding:20px;background:#f8f9fa}
    .card{background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-bottom:20px}
    h2{margin-top:0;color:#333}
    textarea{width:100%;height:80px;padding:10px;font-size:16px;border:2px solid #ddd;border-radius:8px;box-sizing:border-box}
    .row{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
    .row>div{flex:1;min-width:120px}
    label{display:block;font-size:12px;color:#666;margin-bottom:4px}
    select,input[type="range"]{width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;box-sizing:border-box}
    button{padding:12px 24px;font-size:16px;border:none;border-radius:8px;cursor:pointer}
    .btn-primary{background:#007bff;color:#fff}
    .btn-primary:hover{background:#0056b3}
    .btn-primary:disabled{background:#aaa}
    .btn-mic{background:#28a745;color:#fff;position:relative}
    .btn-mic:hover{background:#218838}
    .btn-mic.muted{background:#6c757d!important}
    .btn-mic.muted::after{content:"Мут 10с";position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:10px;background:rgba(0,0,0,0.8);padding:3px 6px;border-radius:10px}
    .btn-mic.recording::after{content:"record";position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:11px;background:rgba(0,0,0,0.8);padding:3px 8px;border-radius:10px}
    #status{margin-top:15px;padding:10px;background:#e9ecef;border-radius:6px;min-height:20px}
    #sttOutput{margin-top:10px;padding:10px;background:#fff3cd;border-radius:6px;min-height:40px;display:none}
    .matched{background:#d4edda!important}
    .not-matched{background:#f8d7da!important}
</style></head><body>
<h2> Peter_the_Great_champ(API)</h2>
<div class="card"><h3>Настройки</h3><div class="row">
    <div><label>Язык TTS</label><select id="language">__LANGUAGES__</select></div>
    <div><label>Спикер</label><select id="speaker">__SPEAKERS__</select></div>
</div><button class="btn-primary" onclick="saveSettings()">Применить</button></div>
<div class="card"><h3> STT(команды)</h3><button id="micBtn" class="btn-mic" onclick="toggleMic()"> Включить микрофон</button><div id="sttOutput"></div><small style="display:block;margin-top:8px;color:#666">🔹 Распознавание только на русском.<br> После озвучки микрофон отключается на 10 секунд.</small></div>
<div class="card"><h3>TTS(озвучивание)</h3><textarea id="text" placeholder="Введите текст..."></textarea>
<div class="row" style="margin-top:10px"><button class="btn-primary" id="speakBtn" onclick="speak()"> Озвучить</button><button class="btn-primary" style="background:#6c757d" onclick="download()"> Скачать</button></div><div id="status"></div></div>
<script>
const API = "__API__";
let audioCtx, stream, scriptProcessor, ws, isRecording = false, prevLang = "ru";
let ttsEndTime = 0;
const MUTE_DURATION = 10000; // 10 секунд

async function loadSettings(){
    try{
        const r = await fetch(API + "/settings");
        const d = await r.json();
        document.getElementById('speaker').value = d.speaker;
        document.getElementById('language').value = d.language;
        prevLang = d.language;
        ttsEndTime = d.tts_end_time || 0;
        updateMicVisual(d.tts_playing);
    }catch(e){console.error("Ошибка загрузки настроек:", e)}
}

function updateMicVisual(isMuted){
    const btn = document.getElementById('micBtn');
    const now = Date.now();
    const isCooling = (now - (ttsEndTime * 1000)) < MUTE_DURATION;
    if (isMuted || isCooling) {
        btn.classList.add('muted');
        btn.classList.remove('recording');
    } else if (isRecording) {
        btn.classList.remove('muted');
        btn.classList.add('recording');
    }
}

async function saveSettings(){
    const speaker = document.getElementById('speaker').value;
    const language = document.getElementById('language').value;
    const status = document.getElementById('status');
    status.textContent = "Сохранение...";
    try{
        const params = new URLSearchParams();
        if (speaker) params.append('speaker', speaker);
        if (language) params.append('language', language);
        await fetch(API + "/settings?" + params.toString(), {method: "POST"});
        status.textContent = "Успешно";
        prevLang = language;
        setTimeout(() => status.textContent = "", 2000);
        loadSettings();
    }catch(e){status.textContent = e.message}
}

async function toggleMic(){
    const btn = document.getElementById('micBtn'), out = document.getElementById('sttOutput');
    if (isRecording) {
        isRecording = false;
        btn.textContent = "Начать распознование";
        btn.classList.remove('recording', 'muted');
        if (stream) stream.getTracks().forEach(t => t.stop());
        if (scriptProcessor) scriptProcessor.disconnect();
        if (audioCtx) audioCtx.close();
        if (ws) ws.close();
        if (prevLang !== "ru") {
            await fetch(API + "/settings?language=" + prevLang, {method: "POST"});
            document.getElementById('language').value = prevLang;
        }
        return;
    }
    try{
        prevLang = document.getElementById('language').value;
        await fetch(API + "/settings?language=ru", {method: "POST"});
        document.getElementById('language').value = "ru";
        
        stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, sampleRate: 16000}});
        audioCtx = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 16000});
        const source = audioCtx.createMediaStreamSource(stream);
        scriptProcessor = audioCtx.createScriptProcessor(4096, 1, 1);

        ws = new WebSocket(API + "/ws/stt");
        ws.binaryType = "arraybuffer";
        
        ws.onmessage = (e) => {
            const d = JSON.parse(e.data);
            out.style.display = "block";
            if (d.matched) {
                out.className = "matched";
                out.innerHTML = `<strong> Команда:</strong> ${d.command}<br><small>Распознано: "${d.text}"</small><br><em> Озвучка: "${d.phrase}"</em>`;
            } else if (d.text) {
                out.className = "not-matched";
                out.textContent = ` "${d.text}" Не является командой`;
            } else {
                out.className = "not-matched";
                out.textContent = ` Пусто`;
            }
        };
        
        scriptProcessor.onaudioprocess = (e) => {
            const now = Date.now();
            if (ttsEndTime && (now - (ttsEndTime * 1000)) < MUTE_DURATION) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            const int16Data = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                const s = Math.max(-1, Math.min(1, inputData[i]));
                int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(int16Data.buffer);
            }
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioCtx.destination);
        
        setInterval(async () => {
            try {
                const r = await fetch(API + "/tts/status");
                const d = await r.json();
                ttsEndTime = d.tts_end_time || ttsEndTime;
                updateMicVisual(d.is_playing);
            } catch(e) {}
        }, 500);
        
        isRecording = true;
        btn.textContent = "";
        btn.classList.add('recording');
        out.style.display = "block";
        out.textContent = "...";
    }catch(err){
        alert("Ошибка: " + err.message);
        if (prevLang !== "ru") fetch(API + "/settings?language=" + prevLang, {method: "POST"}).catch(()=>{});
    }
}

async function speak(){
    const text = document.getElementById('text').value.trim();
    if (!text) return alert("Введите текст!");
    const btn = document.getElementById('speakBtn'), status = document.getElementById('status');
    btn.disabled = true; status.textContent = "Отправка...";
    try{
        const r = await fetch(API + "/speak", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text})
        });
        const d = await r.json();
        status.textContent = d.status === "success" ? "Воспроизводится" : d.detail;
    }catch(e){status.textContent = e.message}
    btn.disabled = false;
}

async function download(){
    const text = document.getElementById('text').value.trim();
    if (!text) return alert("Введите текст!");
    const status = document.getElementById('status');
    status.textContent = "Генерация...";
    try{
        const r = await fetch(API + "/tts/download", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text})
        });
        if (!r.ok) throw new Error(await r.text());
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'tts.wav'; a.click();
        URL.revokeObjectURL(url);
        status.textContent = "Файл скачан";
    }catch(e){status.textContent = e.message}
}

loadSettings();
</script></body></html>"""
    return html.replace("__API__", API_URL).replace("__SPEAKERS__", speakers_html).replace("__LANGUAGES__", languages_html)

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8080, reload=True)