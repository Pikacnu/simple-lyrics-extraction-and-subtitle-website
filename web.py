import re
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from type import WebsocktMessageType
from yt_dlp import YoutubeDL
from whisper_fn import transcribe_audio
import os

YTMUSIC_LINK_MATCH = re.compile(
    r"^(https:\/\/)?(music\.)?youtube\.com\/watch\?v=([a-zA-Z0-9-_]{11}).*")

YTMUSIC_ID_MATCH = re.compile(r"([a-zA-Z0-9-_]{11})")

if not os.path.exists('./downloads'):
    os.makedirs('./downloads/audio')
    os.makedirs('./downloads/lyrics')

app = FastAPI()


@app.get("/")
def root():
    return Response(
        content=open('audio_player.html').read(), media_type="text/html; charset=utf-8"
    )


@app.get("/audio/{dir}")
async def get_audio(request: Request, dir: str):
    file_path = f'./downloads/audio/{dir}'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    header_range = request.headers.get('Range')
    if header_range:
        start, end = header_range.replace('bytes=', '').split('-')
        start = int(start)
        end = int(end) if end else None
        file_size = os.path.getsize(file_path)
        if end is None or end > file_size - 1:
            end = file_size - 1
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(end - start + 1),
            'Content-Type': 'audio/mpeg',
        }
        with open(file_path, 'rb') as f:
            f.seek(start)
            return Response(content=f.read(end - start + 1), headers=headers, media_type="audio/mpeg", status_code=206)
    else:
        file_size = os.path.getsize(file_path)
        headers = {
            'Content-Length': str(file_size),
            'Content-Type': 'audio/mpeg',
            'Accept-Ranges': 'bytes',
        }
        with open(file_path, 'rb') as f:
            return Response(content=f.read(), headers=headers, media_type="audio/mpeg", status_code=200)


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data: WebsocktMessageType = await websocket.receive_json()
            print(data)
            match data["type"]:
                case "link":
                    payload = data["payload"]
                    if not isinstance(payload, str):
                        await websocket.send_json({"type": "error", "payload": "Invalid payload"})
                        continue
                    if not YTMUSIC_LINK_MATCH.match(payload):
                        await websocket.send_json({"type": "error", "payload": "Invalid link"})
                        continue
                    video_id = YTMUSIC_ID_MATCH.search(payload)[0]
                    if not video_id:
                        await websocket.send_json({"type": "error", "payload": "Invalid link"})
                        continue

                    if os.path.exists('./downloads/audio/{video_id}.mp3') or os.path.exists(f'./downloads/lyrics/{video_id}.json'):
                        await websocket.send_json(
                            {"type": "audio", "payload": f'/audio/{video_id}.mp3'})
                        await websocket.send_json({"type": "lyrics", "payload": open(
                            f'./downloads/lyrics/{video_id}.json').read()})
                        continue
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': f'./downloads/audio/{video_id}.%(ext)s',
                    }

                    with YoutubeDL(ydl_opts) as ydl:
                        try:
                            info = ydl.extract_info(payload, download=True)
                            await websocket.send_json(
                                {"type": "audio", "payload": f'/audio/{video_id}.mp3'})
                            await transcribe_audio(video_id, model_name='medium')
                            await websocket.send_json({"type": "lyrics", "payload": open(
                                f'./downloads/lyrics/{video_id}.json').read()})
                            continue
                        except Exception as e:
                            await websocket.send_json({"type": "error", "payload": str(e)})
                            continue
                case _:
                    await websocket.send_json({"type": "error", "payload": "Invalid type"})
                    continue
        except Exception as e:
            if isinstance(e, WebSocketDisconnect):
                break
            await websocket.close()
            break
        except HTTPException as e:
            await websocket.close()
            break
