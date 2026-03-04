## Status

Proposed

Date of decision TBC

## Context and Problem Statement

Minute uses FFmpeg to process audio files. What is the optimal codec (and codec parameters) that minimise CPU time, file size, and maximises transcription quality?

## Considered Options

WAV, FLAC, MP3, AAC, Opus, and MP4. Various codec parameters - see `docmentation/experiments/ffmpeg-varied-codecs.md` for full exploration.

## Decision Outcome

Optimising for CPU time and file size is not a priority - costs associated with these parameters are minimal. Therefore, use whichever codec that results in the highest transcription quality.

This is MP3, sample rate 1600, bitrate 192k, audio channels 1. These parameters are the same as in the source Minute repo.

## Pros and Cons of the Options

Tradeoffs between CPU time, file size, and transcription quality explored in `docmentation/experiments/ffmpeg-varied-codecs.md`.
