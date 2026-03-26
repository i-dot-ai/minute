from evals.audio_generation.src.settings import DEFAULT_VOICES, VOICE_MAP

PYTHONHASHSEED = 0


def get_voice_for_speaker(speaker: str, default_voices: list[str] = DEFAULT_VOICES) -> str:
    if speaker in VOICE_MAP:
        return VOICE_MAP[speaker]

    return default_voices[hash(speaker) % len(default_voices)]
