import stable_whisper
from stable_whisper.result import WhisperResult


def universal_regroup(result: WhisperResult) -> WhisperResult:
    """
    Custom regrouping function that works for multiple languages.
    Regroups segments based on pauses and reasonable segment length.
    """
    # Parameters that work well across languages
    min_pause_for_split = 0.3  # Minimum pause to consider splitting
    max_segment_length = 10.0  # Maximum segment length in seconds
    min_segment_length = 0.5   # Minimum segment length to avoid tiny segments
    
    return result.regroup(min_words_per_segment=1,
                          max_words_per_segment=None,
                          max_chars_per_segment=None,
                          max_segment_duration=max_segment_length,
                          min_segment_duration=min_segment_length,
                          join_punctuations=True,
                          min_pause_duration=min_pause_for_split)


async def transcribe_audio(video_id: str, model_name: str = 'medium'):
    model = stable_whisper.load_faster_whisper(model_name)

    aduio_file_path = f'./downloads/audio/{video_id}.mp3'

    result = model.transcribe(
        aduio_file_path, vad=True, denoiser="demucs", regroup=universal_regroup, word_timestamps=True, ) # type: ignore

    result = model.align(aduio_file_path, result) # type: ignore
    result.save_as_json(f'./downloads/lyrics/{video_id}.json')
