import json
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
    def __init__(self, cache_dir: Path, num_samples: float):
        self.cache_dir = cache_dir
        self.num_samples = num_samples
        self.raw_cache_dir = cache_dir / "raw"
        self.processed_cache_dir = cache_dir / "processed"
        
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)
        self.processed_cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.samples = []
    
    def load_and_prepare_samples(self):
        metadata_cache_path = self.cache_dir / "meeting_metadata.json"
        
        if metadata_cache_path.exists():
            logger.info("Loading cached meeting metadata...")
            with metadata_cache_path.open("r") as f:
                metadata = json.load(f)
            meeting_ids_sorted = metadata["meeting_ids"]
            meeting_durations = metadata["durations"]
            logger.info("Found %d meetings in cache", len(meeting_ids_sorted))
        else:
            logger.info("Loading AMI dataset (ihm configuration - Individual Headset Microphone)...")
            logger.info("This may take a while on first run (downloading full dataset)...")
            
            ds = load_dataset("edinburghcstr/ami", "ihm", split="train")
            
            logger.info("Loaded %d utterances from AMI dataset", len(ds))
            logger.info("Grouping utterances by meeting_id and computing durations...")
            
            meeting_utterances = defaultdict(list)
            
            for example in ds:
                meeting_id = example.get("meeting_id", "unknown")
                meeting_utterances[meeting_id].append(example)
            
            logger.info("Found %d unique meetings in dataset", len(meeting_utterances))
            
            meeting_ids_sorted = sorted(meeting_utterances.keys())
            meeting_durations = {}
            
            for meeting_id in meeting_ids_sorted:
                utterances = meeting_utterances[meeting_id]
                if utterances:
                    max_end_time = max(utt.get("end_time", 0) for utt in utterances)
                    meeting_durations[meeting_id] = max_end_time
            
            metadata = {
                "meeting_ids": meeting_ids_sorted,
                "durations": meeting_durations,
            }
            
            logger.info("Caching meeting metadata...")
            with metadata_cache_path.open("w") as f:
                json.dump(metadata, f)
        
        required_meetings = self._get_required_meetings(meeting_ids_sorted, meeting_durations)
        
        all_cached = all(
            (self.processed_cache_dir / f"{mid}_{idx:06d}.wav").exists()
            for idx, mid in enumerate(required_meetings)
        )
        
        if all_cached:
            logger.info("All required meetings are cached, loading from cache...")
            ds = None
            meeting_utterances = None
        else:
            logger.info("Loading dataset for selected meetings...")
            ds = load_dataset("edinburghcstr/ami", "ihm", split="train")
            
            meeting_utterances = defaultdict(list)
            for example in ds:
                meeting_id = example.get("meeting_id", "unknown")
                if meeting_id in required_meetings:
                    meeting_utterances[meeting_id].append(example)
        
        if self.num_samples < 1.0:
            logger.info("Fractional num_samples detected: %.2f", self.num_samples)
            logger.info("Will collect chunks totaling %.1f%% of first meeting duration", self.num_samples * 100)
            self._process_fractional_samples_optimized(meeting_ids_sorted, meeting_utterances, meeting_durations)
        else:
            num_meetings = int(self.num_samples)
            logger.info("Processing first %d meetings...", num_meetings)
            
            for idx, meeting_id in enumerate(meeting_ids_sorted[:num_meetings]):
                utterances = meeting_utterances[meeting_id] if meeting_utterances else []
                self._process_meeting(meeting_id, utterances, idx)
                
                if (idx + 1) % 5 == 0 or (idx + 1) == num_meetings:
                    logger.info("Combined %d/%d meetings", idx + 1, num_meetings)
        
        logger.info("Dataset preparation complete: %d meetings ready", len(self.samples))
        return self.samples
    
    def _get_required_meetings(self, meeting_ids_sorted: list, meeting_durations: dict) -> set:
        if self.num_samples < 1.0:
            first_meeting_id = meeting_ids_sorted[0]
            first_meeting_duration = meeting_durations.get(first_meeting_id, 0)
            target_duration = first_meeting_duration * self.num_samples
            
            required = set()
            accumulated = 0.0
            
            for meeting_id in meeting_ids_sorted:
                duration = meeting_durations.get(meeting_id, 0)
                if accumulated + duration <= target_duration:
                    required.add(meeting_id)
                    accumulated += duration
                    if accumulated >= target_duration:
                        break
                else:
                    required.add(meeting_id)
                    break
            
            return required
        else:
            num_meetings = int(self.num_samples)
            return set(meeting_ids_sorted[:num_meetings])
    
    def _process_meeting(self, meeting_id: str, utterances: list, idx: int):
        utterances_sorted = sorted(utterances, key=lambda x: x.get("begin_time", 0))
        
        processed_path = self.processed_cache_dir / f"{meeting_id}_{idx:06d}.wav"
        
        if processed_path.exists() and utterances_sorted:
            logger.info("Found cached file for %s, loading from cache", meeting_id)
            mixed_audio, sr = sf.read(processed_path)
            
            full_text = " ".join(utt["text"] for utt in utterances_sorted)
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
            logger.info("Loaded cached meeting %s: %d utterances, %.2f sec, %d words", 
                       meeting_id, len(utterances_sorted), duration, len(full_text.split()))
            return
        elif processed_path.exists() and not utterances_sorted:
            logger.info("Found cached file for %s, loading from cache (no utterances needed)", meeting_id)
            mixed_audio, sr = sf.read(processed_path)
            duration = float(len(mixed_audio) / TARGET_SAMPLE_RATE)
            
            sample = {
                "audio": {
                    "array": mixed_audio,
                    "sampling_rate": TARGET_SAMPLE_RATE,
                    "path": str(processed_path),
                },
                "text": "",
                "meeting_id": meeting_id,
                "dataset_index": idx,
                "duration_sec": duration,
                "num_utterances": 0,
            }
            
            self.samples.append(sample)
            logger.info("Loaded cached meeting %s: %.2f sec (text unavailable)", meeting_id, duration)
            return
        
        if not utterances_sorted:
            logger.warning("No utterances for meeting %s and no cache found, skipping", meeting_id)
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
    
    def _process_fractional_samples_optimized(self, meeting_ids_sorted: list, meeting_utterances: dict, meeting_durations: dict):
        first_meeting_id = meeting_ids_sorted[0]
        first_meeting_duration = meeting_durations.get(first_meeting_id, 0)
        target_duration = first_meeting_duration * self.num_samples
        
        logger.info("First meeting (%s) duration: %.2f sec", first_meeting_id, first_meeting_duration)
        logger.info("Target total duration: %.2f sec (%.1f%% of first meeting)", 
                   target_duration, self.num_samples * 100)
        
        accumulated_duration = 0.0
        chunk_idx = 0
        
        for meeting_id in meeting_ids_sorted:
            meeting_duration = meeting_durations.get(meeting_id, 0)
            utterances = meeting_utterances.get(meeting_id, []) if meeting_utterances else []
            
            if accumulated_duration + meeting_duration <= target_duration:
                self._process_meeting(meeting_id, utterances, chunk_idx)
                
                if len(self.samples) > chunk_idx:
                    actual_duration = self.samples[-1]["duration_sec"]
                    accumulated_duration += actual_duration
                    chunk_idx += 1
                    
                    logger.info("Added meeting %s (%.2f sec), total: %.2f/%.2f sec", 
                               meeting_id, actual_duration, accumulated_duration, target_duration)
                
                if accumulated_duration >= target_duration:
                    logger.info("Reached target duration, stopping collection")
                    break
            else:
                remaining_duration = target_duration - accumulated_duration
                
                if remaining_duration > 0:
                    if utterances:
                        utterances_sorted = sorted(utterances, key=lambda x: x.get("begin_time", 0))
                        partial_utterances = []
                        partial_duration = 0.0
                        
                        for utt in utterances_sorted:
                            utt_duration = utt.get("end_time", 0) - utt.get("begin_time", 0)
                            if partial_duration + utt_duration <= remaining_duration:
                                partial_utterances.append(utt)
                                partial_duration += utt_duration
                            else:
                                break
                        
                        if partial_utterances:
                            fraction_str = f"{self.num_samples:.2f}".replace(".", "_")
                            partial_meeting_id = f"{meeting_id}_frac{fraction_str}"
                            self._process_meeting(partial_meeting_id, partial_utterances, chunk_idx)
                            
                            if len(self.samples) > chunk_idx:
                                actual_duration = self.samples[-1]["duration_sec"]
                                accumulated_duration += actual_duration
                                logger.info("Added partial meeting %s (%.2f sec), total: %.2f/%.2f sec", 
                                           partial_meeting_id, actual_duration, accumulated_duration, target_duration)
                    else:
                        fraction_str = f"{self.num_samples:.2f}".replace(".", "_")
                        partial_meeting_id = f"{meeting_id}_frac{fraction_str}"
                        self._process_meeting(partial_meeting_id, [], chunk_idx)
                        
                        if len(self.samples) > chunk_idx:
                            actual_duration = self.samples[-1]["duration_sec"]
                            accumulated_duration += actual_duration
                            logger.info("Added cached partial meeting %s (%.2f sec), total: %.2f/%.2f sec", 
                                       partial_meeting_id, actual_duration, accumulated_duration, target_duration)
                
                break
        
        logger.info("Fractional collection complete: %d chunks, %.2f sec total", 
                   len(self.samples), accumulated_duration)
    
    def _process_fractional_samples(self, sorted_meetings: list, meeting_durations: dict = None):
        if not sorted_meetings:
            return
        
        first_meeting_id = sorted_meetings[0][0]
        
        if meeting_durations and first_meeting_id in meeting_durations:
            first_meeting_duration = meeting_durations[first_meeting_id]
        else:
            first_utterances = sorted_meetings[0][1]
            first_utterances_sorted = sorted(first_utterances, key=lambda x: x.get("begin_time", 0))
            
            if not first_utterances_sorted:
                return
            
            first_meeting_duration = max(utt.get("end_time", 0) for utt in first_utterances_sorted)
        
        target_duration = first_meeting_duration * self.num_samples
        
        logger.info("First meeting (%s) duration: %.2f sec", first_meeting_id, first_meeting_duration)
        logger.info("Target total duration: %.2f sec (%.1f%% of first meeting)", 
                   target_duration, self.num_samples * 100)
        
        accumulated_duration = 0.0
        chunk_idx = 0
        
        for meeting_id, utterances in sorted_meetings:
            utterances_sorted = sorted(utterances, key=lambda x: x.get("begin_time", 0))
            
            if not utterances_sorted:
                continue
            
            meeting_duration = max(utt.get("end_time", 0) for utt in utterances_sorted)
            
            if accumulated_duration + meeting_duration <= target_duration:
                self._process_meeting(meeting_id, utterances, chunk_idx)
                accumulated_duration += meeting_duration
                chunk_idx += 1
                
                logger.info("Added meeting %s (%.2f sec), total: %.2f/%.2f sec", 
                           meeting_id, meeting_duration, accumulated_duration, target_duration)
                
                if accumulated_duration >= target_duration:
                    logger.info("Reached target duration, stopping collection")
                    break
            else:
                remaining_duration = target_duration - accumulated_duration
                
                if remaining_duration > 0:
                    partial_utterances = []
                    partial_duration = 0.0
                    
                    for utt in utterances_sorted:
                        utt_duration = utt.get("end_time", 0) - utt.get("begin_time", 0)
                        if partial_duration + utt_duration <= remaining_duration:
                            partial_utterances.append(utt)
                            partial_duration += utt_duration
                        else:
                            break
                    
                    if partial_utterances:
                        fraction_str = f"{self.num_samples:.2f}".replace(".", "_")
                        partial_meeting_id = f"{meeting_id}_frac{fraction_str}"
                        self._process_meeting(partial_meeting_id, partial_utterances, chunk_idx)
                        accumulated_duration += partial_duration
                        logger.info("Added partial meeting %s (%.2f sec), total: %.2f/%.2f sec", 
                                   partial_meeting_id, partial_duration, accumulated_duration, target_duration)
                
                break
        
        logger.info("Fractional collection complete: %d chunks, %.2f sec total", 
                   len(self.samples), accumulated_duration)
    
    
    def get_sample(self, idx: int) -> dict:
        if idx < 0 or idx >= len(self.samples):
            raise IndexError(f"Sample index {idx} out of range [0, {len(self.samples)})")
        return self.samples[idx]
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx: int):
        return self.get_sample(idx)


def load_ami_dataset(cache_dir: Path, num_samples: float):
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
