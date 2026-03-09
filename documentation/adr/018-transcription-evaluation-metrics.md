# ADR-018: Transcription Evaluation Metrics

## Status

Proposed

Date of decision: 2026-02-16

## Context and Problem Statement

When evaluating speech-to-text systems against reference transcripts (golden or synthetic), we need appropriate metrics to quantify transcription quality. Different metrics capture different aspects of transcription accuracy, from word-level errors to semantic equivalence and speaker attribution. Which metrics should we use to comprehensively evaluate transcription system performance while providing actionable insights?

## Considered Options

* Word Error Rate (WER)
* Character Error Rate (CER)
* Jaccard Word Error Rate
* Speaker-attributed Word Error Rate (SA-WER)
* Diarization Error Rate (DER)
* Word Diarization Error Rate (WDER) / Speaker Confusion Rate
* Speaker Count Deviation and Accuracy
* Processing Speed / Latency Ratio
* Bidirectional Entailment
* Hedging, Modality, and Register Shift Detection
* Named Entity Recognition (NER) Comparison

## Decision Outcome

WER, WDER, Speaker Count Accuracy, and Processing Speed, because they provide focused, non-noisy coverage of transcription quality from word-level accuracy (WER), speaker attribution (WDER), basic diarization validation (Speaker Count), and processing efficiency (speed ratio) while remaining simple to compute and interpret for comparing providers.

## Pros and Cons of the Options

### Word Error Rate (WER)

*What percentage of words need to be changed to get the perfect transcript (without considering speakers)?*

WER measures the minimum number of word-level edits (insertions, deletions, substitutions) required to transform the hypothesis transcript into the reference transcript, normalized by the reference length.

* Good, because it is easy to compute using standard libraries.
* Good, because it is easy to understand and widely adopted in the field.
* Bad, because it doesn't capture speaker-level information.
* Bad, because it is agnostic to word importance, allowing critical errors to be overshadowed by trivial ones.

### Character Error Rate (CER)

*What percentage of characters need to be changed to get the perfect transcript (without considering speakers)?*

CER measures character-level edits required to transform the hypothesis into the reference, similar to WER but at character granularity.

* Good, because it captures finer-grained errors than WER.
* Bad, because pronunciational inconsistencies in English can spike CER and make it noisy.
* Bad, because it captures similar information to WER but is less interpretable.

### Jaccard Word Error Rate

*What proportion of the expected vocabulary is present in the transcript?*

An extension of WER that considers vocabulary overlap between reference and hypothesis transcripts, measuring what proportion of the expected vocabulary is present rather than exact word-by-word accuracy.

* Good, because it doesn't fall into the trap of overshadowing important words with unimportant ones.
* Good, because it can highlight when key terminology or vocabulary is missing from the transcript.
* Bad, because it is more difficult to explain than standard WER.
* Bad, because it doesn't capture the true number of errors in the text (i.e., how many corrections a scribe would need to make).

### Speaker-attributed Word Error Rate (SA-WER)

*What percentage of words need to be changed to get the perfect transcript (considering speakers)?*

A combined metric that attempts to capture both transcription and diarization quality by computing WER while accounting for speaker attribution.

* Good, because it produces a single headline number for overall system quality.
* Bad, because it is attempting to capture both transcription and diarization quality simultaneously.
* Bad, because it doesn't allow separate analysis of transcription vs. diarization performance.
* Bad, because it can be replaced by WER in conjunction with WDER.

### Diarization Error Rate (DER)

*What proportion of audio time is attributed to the wrong speaker?*

A metric designed for standalone diarization systems, measuring the fraction of time that is incorrectly attributed to speakers.

* Good, because it is well-established for evaluating diarization in isolation.
* Bad, because it is less informative for end-to-end transcription with diarization quality.
* Bad, because it is normalized in terms of time, which is inconsistent with most other metrics presented.
* Bad, because it requires more computational work to compute compared to basic metrics (medium CPU).

### Word Diarization Error Rate (WDER) / Speaker Confusion Rate

*What is the percentage of the words that were transcribed correctly, but were attributed to the wrong speaker?*

Also known as Speaker Confusion Rate, WDER measures speaker attribution errors at the word level.

* Good, because it is modular and can be summed with WER to recover SA-WER (WER + WDER = SA-WER).
* Good, because it isolates diarization quality from transcription quality for separate diagnosis.
* Good, because it is built for end-to-end transcription with diarization systems.
* Bad, because it is not a commonly used metric, requiring careful implementation.
* Bad, because it is not covered by any downstream libraries as far as can be determined.
* Bad, because it requires more computational work to compute compared to basic metrics (medium CPU).

### Speaker Count Deviation and Accuracy

*Did the system recognize the right number of speakers?*

A simple metric counting how many times the detected number of speakers corresponds correctly to the number of speakers present in the reference.

* Good, because it is a simple metric to explain.
* Good, because it identifies a clear mode of failure where incorrect speaker count is always counted as an error.
* Bad, because it doesn't capture other important transcription information.
* Bad, because it can significantly tarnish the perception of an otherwise good transcription (binary pass/fail regardless of deviation magnitude).

### Processing Speed / Latency Ratio

*How fast does the system process audio compared to real-time?*

Measures the ratio of processing time to audio duration, indicating whether the system can transcribe faster or slower than real-time playback.

* Good, because it is trivial to compute (processing time / audio duration).
* Good, because it provides a clear operational metric for comparing provider efficiency.
* Good, because it helps determine if a system is suitable for real-time or near-real-time applications.
* Good, because it is independent of transcription quality, allowing separate evaluation of speed vs. accuracy trade-offs.
* Bad, because it doesn't capture transcription quality or accuracy.
* Bad, because it can vary based on hardware, network conditions, and concurrent load.

### Bidirectional Entailment

*Was the meaning completely preserved, and were extra meanings introduced in the transcription process?*

Uses NLI models to check bidirectional entailment between reference and hypothesis, verifying that all information in each is present in the other, effectively testing semantic equivalence.

* Good, because it can capture non-trivial situations where AI makes mistakes that have high impact on the actual transcript.
* Good, because it can detect contradictions, as contradicting statements will convey contradicting information.
* Good, because it can define a clear failure mode.
* Bad, because if we identify issues, there is very little we can do about the system, especially if other metrics indicate this is the best available option.
* Bad, because it requires significant computational power (e.g., basic AI-capable GPU).
* Bad, because it makes comparing providers difficult due to the complexity and variability of NLI model outputs.

### Hedging, Modality, and Register Shift Detection

*Has the meaning shifted slightly in linguistic terms?*

Detects shifts in linguistic features such as hedging (certainty level), modality (must vs. should), and register (formality level) between reference and hypothesis.

* Good, because it provides an easy way to pinpoint specific types of mistakes.
* Good, because it can capture important quirks where non-crucial but important language features shift (e.g., "must" becoming "should").
* Good, because these shifts can have significant impact on meaning while preserving much of the original semantic content.
* Bad, because addressing these problems is unclear when other metrics show the system is optimal.
* Bad, because it requires significant computational power (e.g., basic AI-capable GPU).
* Bad, because it makes comparing providers difficult due to the complexity and variability of linguistic analysis outputs.

### Named Entity Recognition (NER) Comparison

*Have named entities such as people, organizations, and places been mistranscribed?*

Compares the sets of named entities detected in reference and hypothesis transcripts to identify entity-level errors.

* Good, because it can specifically target errors like mistranscription of names or concepts.
* Good, because it can quickly spot mistakes by comparing entities present in reference but not in hypothesis, and vice versa.
* Bad, because addressing these problems is unclear when other metrics show the system is optimal.
* Bad, because it requires significant computational power (e.g., basic AI-capable GPU).
* Bad, because it makes comparing providers difficult due to the complexity and variability of NER model outputs.

