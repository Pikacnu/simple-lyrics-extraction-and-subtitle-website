import re
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from type import WebsocktMessageType
from yt_dlp import YoutubeDL
from whisper_fn import transcribe_audio
from simple_scrawl import scrawl_lyrics_http
import os
import json
import requests
from typing import Optional, Dict, Any
import stable_whisper

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


async def reposition_lyrics_with_stable_ts(audio_path: str, lyrics_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用stable-ts重新定位歌詞時間戳
    """
    try:
        # 這裡需要根據stable-ts的API進行實際實現
        # 假設stable-ts能接受音頻路徑和原始歌詞，然後返回調整後的歌詞
        # 實際實現可能需要命令行調用或API調用

        # 示例實現：
        # from stable_ts import process_audio
        # return process_audio(audio_path, lyrics_json)

        # 目前只是原樣返回
        text = lyrics_json.get('text', '')
        model = stable_whisper.load_faster_whisper("medium")
        result = model.align(  # type: ignore
            audio_path, text)
        return result.to_json()
    except Exception as e:
        print(f"Stable-TS repositioning error: {e}")
        return lyrics_json


async def get_lyrics_by_video_name(video_name: str, video_id: str) -> Dict[str, Any]:
    """
    根據影片名稱獲取歌詞
    1. 先嘗試HTTP爬取
    2. 若無法獲取，使用whisper
    3. 最後使用stable-ts重新定位歌詞時間戳
    """
    lyrics_path = f'./downloads/lyrics/{video_id}.json'
    audio_path = f'./downloads/audio/{video_id}.mp3'

    # 檢查是否已有歌詞文件
    if os.path.exists(lyrics_path):
        with open(lyrics_path, 'r', encoding='utf-8') as f:
            lyrics_json = json.load(f)
        # 使用stable-ts重新定位
        return await reposition_lyrics_with_stable_ts(audio_path, lyrics_json)

    # 1. 嘗試通過HTTP爬取歌詞
    lyrics_json = scrawl_lyrics_http(video_name)

    if lyrics_json:
        # 保存爬取的歌詞
        with open(lyrics_path, 'w', encoding='utf-8') as f:
            json.dump(lyrics_json, f, ensure_ascii=False, indent=2)
        # 使用stable-ts重新定位
        positioned_lyrics = await reposition_lyrics_with_stable_ts(audio_path, lyrics_json)
        return positioned_lyrics

    # 2. 若HTTP爬取失敗，使用whisper進行轉錄
    await transcribe_audio(video_id, model_name='medium')

    # 讀取whisper生成的歌詞
    with open(lyrics_path, 'r', encoding='utf-8') as f:
        lyrics_json = json.load(f)

    # 3. 使用stable-ts重新定位
    positioned_lyrics = await reposition_lyrics_with_stable_ts(audio_path, lyrics_json)

    # 保存處理後的歌詞
    with open(lyrics_path, 'w', encoding='utf-8') as f:
        json.dump(positioned_lyrics, f, ensure_ascii=False, indent=2)

    return positioned_lyrics


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
                    video_id = YTMUSIC_ID_MATCH.search(
                        payload)[0]  # type: ignore
                    if not video_id:
                        await websocket.send_json({"type": "error", "payload": "Invalid link"})
                        continue

                    # 檢查是否已有音頻文件
                    audio_exists = os.path.exists(
                        f'./downloads/audio/{video_id}.mp3')

                    # 下載音頻文件（如果需要）
                    if not audio_exists:
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
                                if (info is None):
                                    raise Exception(
                                        "Failed to extract video info")
                                video_name = info.get('title', video_id)
                            except Exception as e:
                                await websocket.send_json({"type": "error", "payload": str(e)})
                                continue
                    else:
                        # 如果音頻已存在，嘗試獲取視頻名稱（可能需要額外請求）
                        try:
                            with YoutubeDL({'skip_download': True}) as ydl:
                                info = ydl.extract_info(
                                    payload, download=False)
                                if (info is None):
                                    raise Exception(
                                        "Failed to extract video info")
                                video_name = info.get('title', video_id)
                        except Exception:
                            video_name = video_id  # 如果無法獲取名稱，使用ID代替

                    # 發送音頻路徑
                    await websocket.send_json({"type": "audio", "payload": f'/audio/{video_id}.mp3'})

                    # 獲取歌詞並發送
                    try:
                        lyrics_json = await get_lyrics_by_video_name(video_name, video_id)
                        await websocket.send_json({"type": "lyrics", "payload": lyrics_json})
                    except Exception as e:
                        await websocket.send_json({"type": "error", "payload": f"Error getting lyrics: {str(e)}"})
                    continue
                case _:
                    await websocket.send_json({"type": "error", "payload": "Invalid type"})
                    continue
        except Exception as e:
            if isinstance(e, WebSocketDisconnect):
                break
            await websocket.close()
            break
