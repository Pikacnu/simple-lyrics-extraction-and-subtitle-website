import stable_whisper


async def transcribe_audio(video_id: str, model_name: str = 'medium'):
    model = stable_whisper.load_faster_whisper(model_name)

    aduio_file_path = f'./downloads/audio/{video_id}.mp3'

    result = model.transcribe(aduio_file_path, vad=True, denoiser="demucs")
    result = model.align(aduio_file_path, result)
    result.save_as_json(f'./downloads/lyrics/{video_id}.json')
