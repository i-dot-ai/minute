import logging
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf
from datasets import load_dataset

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000
STEREO_CHANNELS = 2


class AMIDatasetLoader:
    def __init__(self, cache_dir: Path, num_samples: int):
        self.cache_dir = cache_dir
        self.num_samples = num_samples
        self.raw_cache_dir = cache_dir / "raw"
        self.processed_cache_dir = cache_dir / "processed"
        
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)
        self.processed_cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.samples = []
    
    def load_and_prepare_samples(self):
        logger.info("Loading AMI dataset (ihm configuration - Individual Headset Microphone)...")
        logger.info("Combining all utterances per meeting into single audio track...")
        logger.info("This may take a while on first run (downloading full dataset)...")
        
        ds = load_dataset("edinburghcstr/ami", "ihm", split="train")
        
        logger.info("Loaded %d utterances from AMI dataset", len(ds))
        logger.info("Grouping utterances by meeting_id...")
        
        meeting_utterances = defaultdict(list)
        
        for example in ds:
            meeting_id = example.get("meeting_id", "unknown")
            meeting_utterances[meeting_id].append(example)
        
        logger.info("Found %d unique meetings in dataset", len(meeting_utterances))
        
        sorted_meetings = sorted(meeting_utterances.items(), key=lambda x: x[0])
        
        logger.info("Processing first %d meetings...", self.num_samples)
        
        for idx, (meeting_id, utterances) in enumerate(sorted_meetings[:self.num_samples]):
            self._process_meeting(meeting_id, utterances, idx)
            
            if (idx + 1) % 5 == 0 or (idx + 1) == self.num_samples:
                logger.info("Combined %d/%d meetings", idx + 1, self.num_samples)
        
        logger.info("Dataset preparation complete: %d meetings ready", len(self.samples))
        return self.samples
    
    def _process_meeting(self, meeting_id: str, utterances: list, idx: int):
        utterances_sorted = sorted(utterances, key=lambda x: x.get("begin_time", 0))
        
        if not utterances_sorted:
            return
        
        max_end_time = max(utt.get("end_time", 0) for utt in utterances_sorted)
        total_samples = int(np.ceil(max_end_time * TARGET_SAMPLE_RATE))
        
        mixed_audio = np.zeros(total_samples, dtype=np.float32)
        
        combined_text = []
        
        for utt in utterances_sorted:
            audio_array = utt["audio"]["array"]
            sr = utt["audio"]["sampling_rate"]
            begin_time = utt.get("begin_time", 0)
            end_time = utt.get("end_time", 0)
            
            if getattr(audio_array, "ndim", 1) == STEREO_CHANNELS:
                audio_array = audio_array.mean(axis=1)
            
            if sr != TARGET_SAMPLE_RATE:
                audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)
            
            start_sample = int(begin_time * TARGET_SAMPLE_RATE)
            end_sample = start_sample + len(audio_array)
            
            if end_sample > len(mixed_audio):
                end_sample = len(mixed_audio)
                audio_array = audio_array[:end_sample - start_sample]
            
            mixed_audio[start_sample:end_sample] += audio_array
            
            combined_text.append(utt["text"])
        
        max_val = np.abs(mixed_audio).max()
        if max_val > 1.0:
            mixed_audio = mixed_audio / max_val
        
        full_text = " ".join(combined_text)
        
        processed_path = self.processed_cache_dir / f"{meeting_id}_{idx:06d}.wav"
        sf.write(processed_path, mixed_audio, TARGET_SAMPLE_RATE, subtype="PCM_16")
        
        duration = float(len(mixed_audio) / TARGET_SAMPLE_RATE)
        
        sample = {
            "audio": {
                "array": mixed_audio,
                "sampling_rate": TARGET_SAMPLE_RATE,
                "path": str(processed_path),
            },
            "text": full_text,
            "meeting_id": meeting_id,
            "dataset_index": idx,
            "duration_sec": duration,
            "num_utterances": len(utterances_sorted),
        }
        
        self.samples.append(sample)
        logger.info("Mixed meeting %s: %d utterances, %.2f sec, %d words", 
                   meeting_id, len(utterances_sorted), duration, len(full_text.split()))
    
    
    def get_sample(self, idx: int) -> dict:
        if idx < 0 or idx >= len(self.samples):
            raise IndexError(f"Sample index {idx} out of range [0, {len(self.samples)})")
        return self.samples[idx]
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx: int):
        return self.get_sample(idx)


def load_ami_dataset(cache_dir: Path, num_samples: int):
    loader = AMIDatasetLoader(cache_dir, num_samples)
    samples = loader.load_and_prepare_samples()
    
    if samples:
        _validate_dataset_contract(samples[0])
    
    return loader


def _validate_dataset_contract(sample: dict):
    assert "audio" in sample, "Dataset row must contain 'audio'"
    assert "text" in sample, "Dataset row must contain 'text'"
    assert "array" in sample["audio"], "audio must contain 'array'"
    assert "sampling_rate" in sample["audio"], "audio must contain 'sampling_rate'"
    assert isinstance(sample["text"], str), "'text' must be a string transcript"
    
    audio_array = sample["audio"]["array"]
    sampling_rate = sample["audio"]["sampling_rate"]
    
    logger.info("Dataset contract check passed.")
    logger.debug("Example text type: %s", type(sample["text"]))
    logger.debug("Audio array ndim: %s", getattr(audio_array, "ndim", None))
    logger.debug("Audio array shape: %s", getattr(audio_array, "shape", None))
    logger.debug("Sampling rate: %d", sampling_rate)


def audio_duration_seconds(wav_path: str) -> float:
    y, sr = librosa.load(wav_path, sr=None, mono=True)
    return float(len(y) / sr)
