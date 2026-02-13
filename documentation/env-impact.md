# Environmental Impact Assessment

## 1. Overview

The environmental impact of the system is multifaceted and arises from three primary areas:

1. Non-AI infrastructure components (including audio processing)
2. Transcription services
3. Large Language Model (LLM) inference workloads

This assessment focuses on **operational energy use and associated CO₂-equivalent emissions**. Hardware manufacturing, data centre construction, and end-user device impacts are out of scope.

---

## 2. Non-AI Components

### 2.1 Deterministic system elements

The deterministic portion of the system consists of:

* Worker processes
* Back-end services
* Front-end applications
* Database systems
* Queues and messaging infrastructure
* Load balancers and supporting services

These components consume electricity and require cooling in common with most cloud-hosted IT systems. There is little evidence to suggest that this part of the system is significantly more resource-intensive than typical enterprise or public-sector cloud deployments.

### 2.2 Audio processing

> Note: I do remember Jon mentioning that the audio processing is a major contributor to the overall cost, but I don't have any specific numbers and the code doesn't show any major energy consumption considerations. Happy to revise this section if you have any specific numbers.

The system uses **FFmpeg** for converting uploaded audio and video files (including MP4) into a standardized format for transcription processing.

**Conversion workflow:**

* FFmpeg runs locally within the system infrastructure
* Converts any audio/video format to MP3 using the libmp3lame encoder
* Standardizes to mono audio (1 channel) at 192k bitrate
* Extracts audio streams from video files (e.g., MP4)

**Energy characteristics:**

FFmpeg conversion is **moderately CPU-intensive** but benefits from optimization:

* **CPU-intensive operations**: Audio extraction from video containers, re-encoding to MP3, downmixing stereo to mono
* **Efficiency factors**: FFmpeg is a highly optimized C library; 192k bitrate provides reasonable quality without excessive processing; mono output reduces computational load vs. stereo
* **Scale dependency**: Single file conversion has negligible energy cost; batch processing of many or large files can consume significant CPU resources; long videos (hours) are more intensive than typical meeting recordings
* **Built-in optimization**: The system already checks if files are MP3 mono format and skips unnecessary conversions when possible

**Relative impact:**

For typical meeting recordings (30-60 minutes), FFmpeg conversion energy is **minimal compared to transcription and LLM processing** that follow. However, it is not negligible—it represents a measurable CPU workload that scales with file duration and complexity

### 2.3 Optimisation opportunities

**Limited gains through code optimisation**
While software optimisation may marginally reduce compute requirements, the potential environmental benefit is expected to be limited relative to engineering cost, particularly where deterministic components do not dominate total system energy use.

**Cloud provider and region selection**
The most effective lever for reducing environmental impact in this area is infrastructure placement and provider choice, including:

* Selecting regions with lower grid carbon intensity
* Preferring providers that publish or are subject to energy and sustainability reporting

---

## 3. AI and ML Services Impact

### 3.1 Service categories

**Transcription services (ASR)**
Peer-reviewed measurements indicate that cloud-based ASR systems exhibit relatively low energy use and CO₂e per hour of audio, particularly when operated in modern data centres [15].

**Large Language Model services**
LLM inference represents a substantial increase in energy consumption compared to traditional web services. Research indicates that an LLM conversation (500 words in, 500 words out) uses approximately 7 Wh [1], which is roughly 23 times more energy than a comparable Google search (~0.3 Wh) [2].

LLM usage is expected to materially increase the environmental footprint of the overall solution. The computational intensity stems from the massive matrix multiplication operations required—for example, GPT-4 processes approximately 1.76 trillion computations per word processed [12].

### 3.2 Why token usage matters

LLM inference energy scales primarily with:

* Number of input tokens processed
* Number of output tokens generated
* Energy-per-token characteristics of the selected model

For this reason, a **token usage analysis** of each system invocation is used to estimate energy consumption. This analysis is provided in **Appendix B**.

---

## 4. Water Usage Considerations

### 4.1 Context

Water consumption in data centres is a recognised environmental concern. In some regions, high water use has contributed to local water stress and ecosystem impact [3], [5], [6].

### 4.2 European context

Operational water consumption is driven primarily by cooling system design. Industry guidance distinguishes between water withdrawal and water consumption, noting that evaporative cooling is the dominant source of consumptive water use, while dry or closed-loop systems can substantially reduce or eliminate it [1], [6].

In the UK specifically, 51% of data centres use waterless cooling, 44% use hybrid systems, and only 5% use water-based cooling exclusively [6]. Among those that do use water, consumption levels are relatively modest: 33% of UK data centres use less than 1 million litres per year (approximately equivalent to 20 people's annual consumption), and 64% use less than 10 million litres per year (approximately equivalent to 200 people) [6].

It has to be noted that hardware used to train and use AI does require water in the production process [1]. This was not taken into account in the calculations of this report.

### 4.3 Local vs. continental perspective

While 32% of the European population lives in water-stressed areas [5], and water stress is a serious concern in England too (which faces a projected 5 billion litre public water shortage by 2055 [3]), at continental scale, data centres do not represent a major water-consuming sector compared to agriculture and heavy industry [4], [6].

### 4.4 Water cycle considerations

In evaporative cooling systems, water ultimately returns to the broader hydrological cycle through evaporation and precipitation processes [8], [9]. Most data centre water use is non-consumptive—water is returned to the source or hydrologic system shortly after withdrawal, with minimal atmospheric loss and minimal chemical contamination compared to other industrial uses [7], [4].

While this does not negate local water-stress concerns, it supports careful framing of impacts as **local and contextual**, rather than permanent loss. The primary concern is placement: locating high water-use data centres in water-stressed regions compounds existing problems [3], [5].

---

## 5. Quantitative Impact for a 1-Hour Meeting

### 5.1 Key Assumptions

* Transcript length: **X = 9,000 words** (1-hour meeting baseline)
* Token conversion: **2 tokens per word**
* Carbon intensity (inference): **EU-27 average = 0.258 kg CO₂e/kWh** [10]
* Carbon intensity (training): **US average = 0.386 kg CO₂e/kWh** [14]
* ASR emissions from academic measurements [15]
* LLM inference energy from published benchmarking [1]
* LLM training energy from academic papers [11]
* Model selection intentionally pessimistic (Appendix A)
* Token usage formulas assume optimal AI behaviour (no retries/failures)

**See Appendix B.1 for detailed parameters, assumptions, and important limitations.**

### 5.2 Confidence Level

These estimates are **order-of-magnitude approximations** suitable for comparative analysis and strategic decision-making, not precise carbon accounting. Actual values may vary significantly based on speaking pace, model selection, geographic location, and operational conditions.

---

## 6. Transcription Impact (1 Hour)

From the ASR study [15], using Whisper as a proxy (similar open-source ASR system):

**Energy measurements:**
* Average: 0.49 kWh for 22 hours of processing

**Per hour calculation:**
* Energy: 0.49 ÷ 22 ≈ **0.0223 kWh per hour**

**CO₂e emissions:**
* Total: 0.38 kg CO₂e for 22 hours
* Per hour: 0.38 ÷ 22 ≈ **0.0173 kg CO₂e per hour**

**Summary**

| Metric |      Value |
| ------ | ---------: |
| Energy | ~0.022 kWh |
| CO₂e   |  ~0.017 kg |

---

## 7. LLM Processing Impact

### 7.1 SimpleTemplate (General / Executive Summary)

**Token usage** (calculated from Appendix B.2 formulas with X = 9,000)

* GPT-4o (FAST): 74,778 tokens
* GPT-4 Turbo (BEST): 55,916 tokens
* Total: 130,694 tokens

**Energy** (calculated using research benchmarks [1], Appendix E)

* GPT-4o: 45.43 Wh (74,778 tokens × 0.6075 Wh/1k tokens)
* GPT-4 Turbo: 166.07 Wh (55,916 tokens × 2.970 Wh/1k tokens)

**Total LLM energy:** **0.2115 kWh**

**CO₂e**

* 0.2115 × 0.258 = **0.0546 kg CO₂e**

---

### 7.2 SectionTemplate (Y = 6 sections)

**Token usage** (calculated from Appendix B.3 formulas with X = 9,000, Y = 6)

* GPT-4o (FAST): 48,702 tokens
* GPT-4 Turbo (BEST): 177,762 tokens
* Total: 226,464 tokens

**Energy** (calculated using research benchmarks [1], Appendix E)

* GPT-4o: 29.59 Wh (48,702 tokens × 0.6075 Wh/1k tokens)
* GPT-4 Turbo: 527.95 Wh (177,762 tokens × 2.970 Wh/1k tokens)

**Total LLM energy:** **0.5575 kWh**

**CO₂e**

* 0.5575 × 0.258 = **0.1438 kg CO₂e**

---

### 7.3 Delivery Template

**Token usage** (calculated from Appendix B.4 formulas with X = 9,000)

* GPT-4o (FAST): 69,846 tokens
* GPT-4 Turbo (BEST): 50,952 tokens
* Total: 120,798 tokens

**Energy** (calculated using research benchmarks [1], Appendix E)

* GPT-4o: 42.43 Wh (69,846 tokens × 0.6075 Wh/1k tokens)
* GPT-4 Turbo: 151.33 Wh (50,952 tokens × 2.970 Wh/1k tokens)

**Total LLM energy:** **0.1938 kWh**

**CO₂e**

* 0.1938 × 0.258 = **0.0500 kg CO₂e**

---

### 7.4 Basic Minutes (Fallback)

**Token usage** (calculated from Appendix B.5 formulas with X = 9,000)

* GPT-4o (FAST): 83,406 tokens
* GPT-4 Turbo (BEST): 0 tokens (FAST only)
* Total: 83,406 tokens

**Energy** (calculated using research benchmarks [1], Appendix E)

* GPT-4o: 50.67 Wh (83,406 tokens × 0.6075 Wh/1k tokens)

**Total LLM energy:** **0.0507 kWh**

**CO₂e**

* 0.0507 × 0.258 = **0.0131 kg CO₂e**

---

### 7.5 Additional Template Types

Additional AI modes, including UserTemplate FORM, UserTemplate DOCUMENT, AI Edit, and Chat or Interactive Message, are documented in Appendix B.6 but excluded from the main calculations, as they generally require fewer invocations and or FAST-only processing, making them more environmentally friendly.

---

### 7.6 Template Comparison Summary

| Template Type | Invocations | Total Tokens | Energy (kWh) | CO₂e (kg) |
|---------------|-------------|--------------|--------------|-----------|
| Basic Minutes | 4 | 83,406 | 0.0507 | 0.0131 |
| Delivery | 6 | 120,798 | 0.1938 | 0.0500 |
| SimpleTemplate | 6 | 130,694 | 0.2115 | 0.0546 |
| SectionTemplate (Y=6) | 17 | 226,464 | 0.5575 | 0.1438 |

**Key observations:**
* Model selection, FAST versus BEST, has a greater impact than token count alone
* The architectural decision in Minute to separate these two types of invocation is the primary driver of emissions reduction
* Emissions can vary greatly between templates

---

## 8. Combined Impact per 1-Hour Meeting

### 8.1 SimpleTemplate

| Component      | Energy (kWh) | % of Total |  CO₂e (kg) | % of Total |
| -------------- | -----------: | ---------: | ---------: | ---------: |
| Transcription  |       0.0223 |       9.5% |     0.0173 |      24.1% |
| LLM processing |       0.2115 |      90.5% |     0.0546 |      75.9% |
| **Total**      |   **0.2338** | **100.0%** | **0.0719** | **100.0%** |

### 8.2 SectionTemplate (Y=6)

| Component      | Energy (kWh) | % of Total |  CO₂e (kg) | % of Total |
| -------------- | -----------: | ---------: | ---------: | ---------: |
| Transcription  |       0.0223 |       3.8% |     0.0173 |      10.7% |
| LLM processing |       0.5575 |      96.2% |     0.1438 |      89.3% |
| **Total**      |   **0.5798** | **100.0%** | **0.1611** | **100.0%** |

### 8.3 Delivery Template

| Component      | Energy (kWh) | % of Total |  CO₂e (kg) | % of Total |
| -------------- | -----------: | ---------: | ---------: | ---------: |
| Transcription  |       0.0223 |      10.3% |     0.0173 |      25.7% |
| LLM processing |       0.1938 |      89.7% |     0.0500 |      74.3% |
| **Total**      |   **0.2161** | **100.0%** | **0.0673** | **100.0%** |

### 8.4 Basic Minutes

| Component      | Energy (kWh) | % of Total |  CO₂e (kg) | % of Total |
| -------------- | -----------: | ---------: | ---------: | ---------: |
| Transcription  |       0.0223 |      30.5% |     0.0173 |      56.9% |
| LLM processing |       0.0507 |      69.5% |     0.0131 |      43.1% |
| **Total**      |   **0.0730** | **100.0%** | **0.0304** | **100.0%** |

### 8.5 Comprehensive Template Comparison (Total System Impact)

| Template Type | Total Energy (kWh) | Total CO₂e (kg) | Relative to Basic |
|---------------|-------------------:|----------------:|------------------:|
| Basic Minutes | 0.0730 | 0.0304 | 1.0× |
| Delivery | 0.2161 | 0.0673 | 3.0× |
| SimpleTemplate | 0.2338 | 0.0719 | 3.2× |
| SectionTemplate (Y=6) | 0.5798 | 0.1611 | 7.9× |

---

## 9. Interpretation

**Energy distribution patterns:**
* LLM inference dominates operational energy use across all template types, representing 70-96% of total energy consumption depending on template complexity
* Basic Minutes shows the most balanced distribution (70% LLM, 30% transcription) due to minimal processing
* SectionTemplate shows highest LLM dominance (96%) due to multiple BEST model invocations
* Transcription represents a fixed cost of 0.0223 kWh regardless of template type

**Total system impact:**
* The combined transcription and processing workflow for a 1-hour meeting produces **0.03-0.16 kg CO₂e** depending on template choice
* Range spans from Basic Minutes (0.030 kg) to SectionTemplate (0.161 kg) - a 5.3× difference
* Template selection is the single most impactful factor for environmental footprint

---

## 10. AI Model Training Impact

Model training represents a substantial one-time energy investment amortized across all users. Following the Final Discovery Report methodology, we distribute training costs equally across all users on a subscription basis. Training emissions are one-time costs, unlike inference costs which recur with each use.

This system uses two types of AI models: Large Language Models (LLMs) for summarization and Speech-to-Text (ASR) models for transcription. Both contribute to the overall training footprint.

### 10.1 Per-User Training Impact

**LLM models:** Assuming that the system uses GPT-4 Turbo (BEST pathway) and GPT-4o (FAST pathway). GPT-4 is a large model (~1.76 trillion parameters) with training energy estimated at ~57,000 MWh [11]. GPT-4o is a smaller, more efficient model (~200 billion parameters) using Gopher as a training proxy (~1,151 MWh) [11] [12]. Training costs are amortized across 800 million weekly active users [13].

**ASR models:** Using OWSM v3 as a proxy for Whisper-style ASR models, training energy is estimated at ~7.4 MWh [19]. Training costs are amortized across 300 million Microsoft Teams monthly active users [23].

**Per-user training impacts:**

| Model | Training Energy | Per-User Energy | Per-User CO₂e |
|-------|----------------|-----------------|---------------|
| GPT-4 (Turbo) | ~57,000 MWh | 0.071 kWh | 0.027 kg |
| GPT-4o | ~1,151 MWh | 0.0014 kWh | 0.00054 kg |
| ASR (OWSM v3 proxy) | ~7.4 MWh | 0.000025 kWh | 0.0000095 kg |
| **System Total** | - | **0.072 kWh** | **0.028 kg** |

*ASR training represents only 0.034% of combined training impact and is negligible.*

*See Appendices D and E for detailed calculation methodology and data sources.*

### 10.2 Training vs. Inference Comparison

**Combined training impact (both models):** 0.072 kWh, 0.028 kg CO₂e per user

**1-hour SimpleTemplate meeting:** 0.234 kWh, 0.072 kg CO₂e

**Key finding:** Processing a single 1-hour meeting with SimpleTemplate consumes **3.2× the combined training cost** amortized per user (GPT-4 + GPT-4o). This means:
* Training represents only ~31% of a single meeting's inference cost
* After processing just one meeting, inference costs exceed the user's share of training costs
* Inference costs accumulate with each use, rapidly dominating the environmental impact

**Limitations:** Equal-distribution approach does not reflect actual usage patterns but provides a tractable baseline. Training estimates are based on independent research and may not reflect actual configurations. With 800 million users, training costs are well-amortized; smaller user bases would see proportionally higher per-user impact.
* Actual training may have included multiple runs, failed attempts, or iterative improvements not captured in published estimates
* The GPT-4o estimate uses Gopher as a proxy due to similar parameter counts, but architectural differences may affect actual training costs

**Carbon intensity for training:**

Training calculations use US average carbon intensity (0.386 kg CO₂e/kWh) from EPA eGRID data [14], as most large-scale AI training is conducted in US data centres. This is significantly higher than the EU-27 average (0.258 kg CO₂e/kWh) used for inference calculations, reflecting the carbon-intensive nature of US electricity generation.

**Scope boundaries:**

This analysis includes only the energy consumed during the final training run(s) that produced the deployed models. It excludes:
* Research and development iterations
* Preliminary experiments and ablation studies
* Infrastructure manufacturing and deployment
* Ongoing fine-tuning and model updates

For comprehensive lifecycle assessment, these additional factors would need to be considered, potentially increasing training impact estimates by a factor of 2-10×.

---

# Appendix A: Model Selection

To avoid underestimating environmental impact, this assessment assumes comparatively energy-intensive but commonly used models for inference, based on published benchmarking. This produces **pessimistic but defensible estimates**. Actual emissions will vary with deployed models, prompt structure, and batching behaviour.

---

# Appendix B: System Token Usage Analysis

This appendix documents all LLM invocations in the i-ai-minute system with per-invocation token estimates and source file references.

## B.1 Parameters and Assumptions

### Parameters

* **X** = words in meeting transcript (9,000 words baseline for 1-hour meeting)
* **Y** = number of sections (SectionTemplate only, typically 6)
* **Q** = number of questions (UserTemplate FORM type)

### Token Conversion Assumptions

* **2 tokens per word** (conservative estimate for English text)
* **Transcript length (X)**: 7,500-9,000 words for 1-hour meeting, based on typical conversation speed
* Actual transcripts may vary significantly (5,000-15,000 words/hour) depending on speaking pace, silences, and meeting dynamics
* Different models use different tokenization schemes; actual token counts will vary

### Key Assumptions

* SimpleTemplate and SectionTemplate are mutually exclusive per meeting
* Hallucination checks follow their corresponding LLM invocations when enabled (assumed on)
* Citations added only when `citations_required = True` (assumed on)
* Formulas assume optimal AI behaviour (no retries, failures, or regenerations)
* Retry logic with exponential backoff (max 6 attempts) not counted in estimates
* Formulas based on rough estimates of AI behaviour and assume non-reasoning models

### Energy Scaling Assumptions

* **ASR**: Energy scales linearly with audio duration (reasonable for transcription services)
* **LLMs**: Energy scaling with token count is approximately proportional but nuanced due to batch processing, attention mechanisms, and model architecture
* These provide reasonable estimates but should not be treated as precise measurements

### Geographic Scope and Carbon Intensity

* **Inference**: EU-27 average (0.258 kg CO₂e/kWh) as baseline for operational use
* **Training**: US average (0.386 kg CO₂e/kWh) from EPA eGRID data, as most large-scale AI training occurs in US data centres
* Actual carbon intensity varies significantly by region, provider, and time of day
* Many AI providers route queries to various global data centres with different carbon intensities
* Organizations in different regions will see proportionally different CO₂e impacts
* Relative energy consumption patterns remain valid regardless of location

### Training Impact Methodology

* Training costs distributed equally across all users (subscription basis approach)
* This equal-distribution method is not representative of actual usage patterns but provides tractable estimation framework
* Training is one-time cost amortized over model lifetime, unlike recurring inference costs
* User base estimates based on peak active users and may underestimate total lifetime users

### Scope Limitations

* **Included**: Operational inference and training energy
* **Excluded**:
  * Data collection and experimentation (FacebookAI reported 31% of lifetime ML power use [18])
  * Experiments (FacebookAI reported 10% of lifetime ML power use [18])
  * Model development iterations, infrastructure manufacturing, ongoing fine-tuning
  * Hardware manufacturing emissions for training infrastructure
  * LLM usage for evaluation and template creation (small one-time cost during system setup)
* For comprehensive lifecycle assessment, excluded factors could increase estimates by 2-10×

### Research Quality Considerations

Primary studies [1], [11], [15] represent decent available research but have limitations:
* Neither represents cutting-edge peer-reviewed research from top-tier venues (field still in infancy, often overlooked by main academic venues)
* Methodologies are sound with no major red flags identified
* Selected because independent research in this area is extremely limited
* AI company self-reported figures avoided due to falsification incentives and precedence for underreporting [16], [17]
* As more rigorous independent research emerges, these estimates should be updated

### Model Definitions

* **FAST**: GPT-4o (configured via `FAST_LLM_PROVIDER` and `FAST_LLM_MODEL_NAME`)
* **BEST**: GPT-4 Turbo (configured via `BEST_LLM_PROVIDER` and `BEST_LLM_MODEL_NAME`)

## B.2 SimpleTemplate Templates

**Templates**: General, ExecutiveSummary, CareAssessmentV2  
**Source**: `common/templates/types.py:92-103`  
**Total invocations**: 6

| # | Invocation      | Model | File Reference | Input (words) | Output (words) |
| - | --------------- | ----- | -------------- | ------------: | -------------: |
| 1 | Speaker ID      | FAST  | `common/audio/generate_speaker_predictions.py:37-43` | 82 + X | 40 |
| 2 | Title           | FAST  | `common/generate_meeting_title.py:14-16` | 18 + X | 15 |
| 3 | Minutes         | BEST  | `common/templates/types.py:96-97` | 430 + X | 0.5X |
| 4 | Hallucination 1 | BEST  | `common/templates/types.py:98` | 448 + 1.5X | 80 |
| 5 | Citations       | FAST  | `common/templates/citations.py:12-15` | 118 + 1.55X | 0.5X |
| 6 | Hallucination 2 | FAST  | `common/templates/citations.py:12-15` | 136 + 2.05X | 80 |

**Totals (words):**
* FAST: 354 + 3.6X input, 135 + 0.5X output
* BEST: 878 + 2.5X input, 80 + 0.5X output
* Grand total: 1,232 + 6.1X input, 215 + X output

## B.3 SectionTemplate Templates

**Templates**: Cabinet, PlanningCommittee  
**Source**: `common/templates/types.py:163-196`  
**Total invocations**: 5 + 2Y

| # | Invocation           | Model | File Reference | Input (words) | Output (words) |
| - | -------------------- | ----- | -------------- | ------------: | -------------: |
| 1 | Speaker ID           | FAST  | `common/audio/generate_speaker_predictions.py:37-43` | 82 + X | 40 |
| 2 | Title                | FAST  | `common/generate_meeting_title.py:14-16` | 18 + X | 15 |
| 3 | Section detection    | FAST  | `common/templates/default/cabinet.py:190-195` | 56 + X | 2Y |
| 4a | First section       | BEST  | `common/templates/types.py:176-181` | 1,615 + X | 0.3X/Y |
| 4b | Each additional section (×Y-1) | BEST | `common/templates/types.py:185-186` | 18 | 0.3X/Y |
| 5 | Hallucination per section (×Y) | BEST | `common/templates/types.py:183,187` | 18 + 1.3X/Y | 80 |
| 6 | Citations            | FAST  | `common/templates/citations.py:12-15` | 118 + 1.35X | 0.3X |
| 7 | Hallucination 2      | FAST  | `common/templates/citations.py:12-15` | 136 + 1.65X | 80 |

**Totals (words):**
* FAST: 354 + 2.35X input, 135 + 2Y + 0.3X output
* BEST: 1,633 + 1,575Y + 58Y² + 1.15X + 1.15XY input, 80 + 80Y + 0.3X output
* Grand total: 1,987 + 1,575Y + 58Y² + 3.5X + 1.15XY input, 215 + 82Y + 0.6X output

## B.4 Delivery Template

**Source**: `common/templates/default/delivery.py:73-107`  
**Total invocations**: 6

| # | Invocation           | Model | File Reference | Input (words) | Output (words) |
| - | -------------------- | ----- | -------------- | ------------: | -------------: |
| 1 | Speaker ID           | FAST  | `common/audio/generate_speaker_predictions.py:37-43` | 82 + X | 40 |
| 2 | Title                | FAST  | `common/generate_meeting_title.py:14-16` | 18 + X | 15 |
| 3 | Sections + Actions   | BEST  | `common/templates/default/delivery.py:81-83` | 65 + X | 0.4X |
| 4 | Attendees            | BEST  | `common/templates/default/delivery.py:86` | 18 | 30 |
| 5 | Hallucination        | BEST  | `common/templates/default/delivery.py:84` | 83 + 1.4X | 80 |
| 6 | Citations            | FAST  | `common/templates/citations.py:12-15` | 118 + 1.45X | 0.4X |

**Totals (words):**
* FAST: 218 + 3.45X input, 55 + 0.4X output
* BEST: 166 + 2.4X input, 110 + 0.4X output
* Grand total: 384 + 5.85X input, 165 + 0.8X output

## B.5 Basic Minutes (Fallback)

**Source**: `common/services/minute_handler_service.py:221-228`  
**Total invocations**: 4

| # | Invocation      | Model | File Reference | Input (words) | Output (words) |
| - | --------------- | ----- | -------------- | ------------: | -------------: |
| 1 | Speaker ID      | FAST  | `common/audio/generate_speaker_predictions.py:37-43` | 82 + X | 40 |
| 2 | Title           | FAST  | `common/generate_meeting_title.py:14-16` | 18 + X | 15 |
| 3 | Basic summary   | FAST  | `common/services/minute_handler_service.py:225-226` | 25 + X | 0.3X |
| 4 | Hallucination   | FAST  | `common/services/minute_handler_service.py:227` | 43 + 1.3X | 80 |

**Totals (words):**
* FAST only: 168 + 3.3X input, 135 + 0.3X output
* Grand total: 168 + 3.3X input, 135 + 0.3X output

## B.6 Additional Template Types (Not in Main Calculations)

**UserTemplate (DOCUMENT type)**: 4 invocations (2 FAST, 2 BEST)  
**UserTemplate (FORM type)**: 2 + Q invocations (FAST only, where Q = number of questions)  
**AI Edit**: 2 invocations per edit (all FAST)  
**Chat/Interactive Message**: 1 invocation per message (FAST)

These patterns represent specialized workflows not used in typical meeting processing.

---

# Appendix D: Training Impact Calculation Details

## D.1 Data Sources and Assumptions

**GPT-4 Training Energy:**
* Source: Ji, Z. & Jiang, M. "A systematic review of electricity demand for large language models" [11]
* Estimated range: 52,000-62,000 MWh
* Midpoint used: 57,000 MWh (57,000,000 kWh)
* Uncertainty: ±5,000 MWh (±9%)

**GPT-4o Training Energy:**
* Parameter count: ~200 billion [12]
* Proxy model: DeepMind Gopher (280 billion parameters)
* Training energy from [11]: 1,151 MWh (1,151,000 kWh)
* Scaling assumption: Linear relationship between parameters and training energy at this scale

**User Base:**
* Source: TechCrunch reporting on OpenAI announcements [13]
* Weekly active users at peak: 800 million
* Assumption: Peak weekly active users represents the relevant amortization base
* Note: This likely underestimates total lifetime users but provides a conservative estimate

**Carbon Intensity:**
* US average: 0.386 kg CO₂e/kWh (EPA eGRID) [14]
* Note: Training calculations use US carbon intensity as most large-scale AI training occurs in US data centers
* This is significantly higher than EU-27 average (0.258 kg CO₂e/kWh) used for inference

## D.2 Calculation Methodology

**GPT-4 per-user calculations:**

```
Training energy total: 57,000,000 kWh
User base: 800,000,000 users
Energy per user = 57,000,000 ÷ 800,000,000 = 0.071 kWh
CO₂e per user = 0.071 kWh × 0.386 kg CO₂e/kWh = 0.027 kg CO₂e
```

**GPT-4o per-user calculations:**

```
Training energy total: 1,151,000 kWh
User base: 800,000,000 users
Energy per user = 1,151,000 ÷ 800,000,000 = 0.0014 kWh
CO₂e per user = 0.0014 kWh × 0.386 kg CO₂e/kWh = 0.00054 kg CO₂e
```

**Combined system impact:**

```
GPT-4 + GPT-4o total: 0.072 kWh/user, 0.028 kg CO₂e/user
```

**Comparison to 1-hour SimpleTemplate meeting:**

```
SimpleTemplate (1h meeting): 0.234 kWh, 0.072 kg CO₂e
Training (per user):         0.072 kWh, 0.028 kg CO₂e
Ratio: 0.234 ÷ 0.072 = 3.2×

Inference consumes 3.2× the amortized training cost per user.
```

---

# Appendix E: Speech-to-Text Training Impact — OWSM Case Study

## E.1 Context and Relevance

This appendix examines the training energy requirements for **Open Whisper-style Speech Models (OWSM)** [19], which represent open-source alternatives to proprietary ASR systems like OpenAI's Whisper. Understanding S2T training costs provides important context for the transcription services used in this system.

**Why OWSM as a case study:**
- OWSM models explicitly reproduce Whisper-style training using open-source toolkits
- Training methodology and resource requirements are publicly documented

**Relationship to this system:**
While this system uses commercial transcription services (not OWSM), this case study illustrates the one-time training costs that underpin modern ASR capabilities. Similar to LLM training costs (Appendix D), these costs are amortized across all users of the technology.

**Limitation:**
This analysis does not account for the energy used by auxialiary AI systems (e.g. diarization, content moderation) that are bundled in the transcription services used in this system.

---

## E.2 OWSM v3 Training Configuration

This analysis focuses on OWSM v3 [19], which represents a standard medium-sized Whisper-style model:

| Model | GPUs | Duration | Training Data |
|-------|------|----------|---------------|
| OWSM v3 | 64 A100s | 10 days | 180k hours |

The model uses NVIDIA A100 40GB PCIe GPUs with 250W TDP [20].

---

## E.3 Energy Calculation Methodology

### Base GPU Energy

```
64 GPUs × 250W × 24h × 10 days = 3,840 kWh
```

### System Overhead

GPUs do not operate in isolation. According to Netrality Data Centers [22]:
> "A server with eight A100 GPUs draws 3,200 watts just for GPUs, plus another 500-1,000 watts for CPUs, memory, and other components."

Calculation:
- Midpoint: 750W / 3,200W = additional 23.44%
- System overhead multiplier: 1.2344×

This accounts for CPUs, memory, networking, storage, and other server components required to support GPU training.

### Datacenter Infrastructure (PUE)

The Uptime Institute Global Data Center Survey 2024 [21] reports:
> "In the 2024 survey results, the industry average PUE of 1.56 reveals a continuing trend of inertia"

PUE multiplier: 1.56×

PUE (Power Usage Effectiveness) captures cooling, power distribution losses, lighting, and other facility-level overhead. A PUE of 1.56 means that for every 1 kWh consumed by IT equipment providing value directly to users, an additional 0.56 kWh is consumed by everything else.

---

## E.4 Complete Training Energy Impact

| Tier | Description | OWSM v3 |
|------|-------------|----------|
| Tier 1 | GPU only | 3,840 kWh |
| Tier 2 | + System overhead (×1.2344) | 4,740 kWh |
| Tier 3 | + Datacenter PUE (×1.56) | 7,395 kWh |

---

## E.5 Interpretation and Context

### Comparison to LLM Training

| Model Type | Training Energy |
|------------|----------------|
| OWSM v3 | 7,395 kWh |
| GPT-4 (estimated) | 57,000,000 kWh |
| GPT-4o (estimated) | 1,151,000 kWh |

Key observations:
- S2T training is 7,700× less energy-intensive than GPT-4 training
- S2T training is 156× less energy-intensive than GPT-4o training

---

## E.6 Per-User Training Impact

**User base:** Training costs amortized across 300 million Microsoft Teams monthly active users [23], representing a conservative estimate for Azure Speech-to-Text service reach.

**Carbon intensity:** US average 0.386 kg CO₂e/kWh (EPA eGRID) [14], as most large-scale AI training occurs in US data centers.

## E.7 Calculation Methodology

**OWSM v3 per-user calculations:**

```
Training energy total: 7,395 kWh
User base: 300,000,000 users
Energy per user = 7,395 ÷ 300,000,000 = 0.000025 kWh
CO₂e per user = 0.000025 kWh × 0.386 kg CO₂e/kWh = 0.0000095 kg CO₂e
```

**Combined system training impact (LLM + ASR):**

```
GPT-4 + GPT-4o:  0.072 kWh/user,    0.028 kg CO₂e/user
OWSM v3 (ASR):   0.000025 kWh/user, 0.0000095 kg CO₂e/user
Total:           0.072 kWh/user,    0.028 kg CO₂e/user
```

**Key observation:** ASR training represents only 0.034% of the combined training impact per user, making it negligible in the overall training footprint.

---

# Appendix E: LLM Energy Consumption Benchmarks

This appendix provides empirical energy consumption data for major LLM models, derived from independent research measurements [1]. These values are used throughout this assessment to calculate operational energy costs.

## E.1 Data Source

All energy consumption values are taken from **Table 4** of Jegham et al., "How Hungry is AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference" (arXiv:2505.09598v6, Nov. 2025) [1].

The research measured actual energy consumption across three prompt sizes:
* **Small**: 100 input tokens, 300 output tokens
* **Medium**: 1,000 input tokens, 1,000 output tokens  
* **Large**: 10,000 input tokens, 1,500 output tokens

Values represent mean ± standard deviation in watt-hours (Wh).

## E.2 Energy Consumption by Model

### OpenAI Models

| Model | Small (100/300) | Medium (1k/1k) | Large (10k/1.5k) |
|-------|-----------------|----------------|------------------|
| GPT-4.1 | 0.871 ± 0.302 Wh | 3.161 ± 0.515 Wh | 4.833 ± 0.650 Wh |
| GPT-4.1 mini | 0.450 ± 0.081 Wh | 1.545 ± 0.211 Wh | 2.122 ± 0.348 Wh |
| GPT-4.1 nano | 0.207 ± 0.047 Wh | 0.575 ± 0.108 Wh | 0.827 ± 0.094 Wh |
| o4-mini (high) | 3.649 ± 1.468 Wh | 7.380 ± 2.177 Wh | 7.237 ± 1.674 Wh |
| o3 | 1.177 ± 0.224 Wh | 5.153 ± 2.107 Wh | 12.222 ± 1.082 Wh |
| o3-mini (high) | 3.012 ± 0.991 Wh | 6.865 ± 1.330 Wh | 5.389 ± 1.183 Wh |
| o3-mini | 0.674 ± 0.015 Wh | 2.423 ± 0.237 Wh | 3.525 ± 0.168 Wh |
| o1 | 2.268 ± 0.654 Wh | 4.047 ± 0.497 Wh | 6.181 ± 0.877 Wh |
| o1-mini | 0.535 ± 0.182 Wh | 1.547 ± 0.405 Wh | 2.317 ± 0.530 Wh |
| **GPT-4o (Mar '25)** | **0.423 ± 0.085 Wh** | **1.215 ± 0.241 Wh** | **2.875 ± 0.421 Wh** |
| GPT-4o mini | 0.577 ± 0.139 Wh | 1.897 ± 0.570 Wh | 3.098 ± 0.639 Wh |
| **GPT-4 Turbo** | **1.699 ± 0.355 Wh** | **5.940 ± 1.441 Wh** | **9.877 ± 1.304 Wh** |
| GPT-4 | 1.797 ± 0.259 Wh | 6.925 ± 1.553 Wh | — |

### Anthropic Models

| Model | Small (100/300) | Medium (1k/1k) | Large (10k/1.5k) |
|-------|-----------------|----------------|------------------|
| Claude-3.7 Sonnet | 0.950 ± 0.040 Wh | 2.989 ± 0.201 Wh | 5.671 ± 0.302 Wh |
| Claude-3.5 Sonnet | 0.973 ± 0.066 Wh | 3.638 ± 0.256 Wh | 7.772 ± 0.345 Wh |
| Claude-3.5 Haiku | 0.975 ± 0.063 Wh | 4.464 ± 0.283 Wh | 8.010 ± 0.338 Wh |

## E.3 Models Used in This Assessment

This assessment uses the following models for calculations:

* **FAST pathway**: GPT-4o (March 2025)
* **BEST pathway**: GPT-4 Turbo

These models are highlighted in bold in the tables above.

## E.4 Calculation Methodology

Energy consumption for this system's workload is calculated by:

1. **Estimating total token count** from invocation formulas (Appendix B)
2. **Converting to equivalent prompt size** using the medium (1k/1k) benchmark as baseline
3. **Scaling energy proportionally** based on actual token counts
4. **Using mean values** from the research data (standard deviation noted but not propagated)

**Per-token energy rates used:**

From the medium (1k/1k) measurements:
* **GPT-4o**: 1.215 Wh per 2,000 tokens = **0.6075 Wh per 1,000 tokens**
* **GPT-4 Turbo**: 5.940 Wh per 2,000 tokens = **2.970 Wh per 1,000 tokens**

These rates assume linear scaling with token count, which is a reasonable approximation for inference workloads of similar size to the benchmark conditions.


---

# References

[1] N. Jegham, M. Abdelatti, C. Y. Koh, L. Elmoubarki and A. Hendawi, "How Hungry is AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference," arXiv:2505.09598v6, Nov. 2025. [Online]. Available: https://arxiv.org/abs/2505.09598

[2] U. Hölzle, "Powering a Google search," *Google Public Policy Blog*, Jan. 11, 2009. [Online]. Available: https://googleblog.blogspot.com/2009/01/powering-google-search.html

[3] Environment Agency, "England faces 5 billion litre public water shortage by 2055 without urgent action," GOV.UK, Jun. 2025. [Online]. Available: https://www.gov.uk/government/news/england-faces-5-billion-litre-public-water-shortage-by-2055-without-urgent-action

[4] European Environment Agency, "Water abstraction by economic sector in Europe." [Online]. Available: https://www.eea.europa.eu/en/analysis/indicators/water-abstraction-by-source-and/water-abstraction-by-economic-sector

[5] European Environment Agency, “Water scarcity conditions in Europe,” *EEA Briefing*, 2025. [Online]. Available: https://www.eea.europa.eu/en/analysis/indicators/use-of-freshwater-resources-in-europe-1

[6] techUK, "Understanding data centre water use in England," London, UK, Aug. 2025. [Online]. Available: https://www.techuk.org/static/c5d37a41-6eb9-4d41-8ed3036030936814/techUK-ReportUnderstanding-Data-Centre-Water-Use-in-EnglandAugust-2025.pdf

[7] Sustainability Directory, "Non-Consumptive Water Use," 2025. [Online]. Available: https://term.sustainability-directory.com/term/non-consumptive-water-use

[8] U.S. Geological Survey, "Evaporation and the Water Cycle: Evaporation," U.S. Geological Survey Water Science School. [Online]. Available: https://www.usgs.gov/water-science-school/science/evaporation-and-water-cycle

[9] National Oceanic and Atmospheric Administration, "The Water Cycle," NOAA Education. [Online]. Available: https://www.noaa.gov/education/resource-collections/freshwater/water-cycle

[10] European Environment Agency, "Greenhouse Gas Emission Intensity of Electricity Generation in Europe (EU-27)." [Online]. Available: https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1 

[11] Z. Ji and M. Jiang, "A systematic review of electricity demand for large language models: evaluations, challenges, and solutions," *Renewable and Sustainable Energy Reviews*, vol. 225, p. 116159, 2026. [Online]. Available: https://www.sciencedirect.com/science/article/pii/S1364032125008329

[12] A. Ben Abacha, W.-w. Yim, Y. Fu, Z. Sun, M. Yetisgen, F. Xia and T. Lin, "MEDEC: A Benchmark for Medical Error Detection and Correction in Clinical Notes," arXiv:2412.19260, Jan. 2, 2025. [Online]. Available: https://arxiv.org/abs/2412.19260

[13] K. Wiggers, "Sam Altman says ChatGPT has hit 800M weekly active users," *TechCrunch*, Oct. 6, 2025. [Online]. Available: https://techcrunch.com/2025/10/06/sam-altman-says-chatgpt-has-hit-800m-weekly-active-users/

[14] U.S. Environmental Protection Agency, "Emissions & Generation Resource Integrated Database (eGRID)," EPA. [Online]. Available: https://www.epa.gov/egrid

[15] J. El Bahri, M. Kouissi and M. Achkari Begdouri, "Comparative Analysis of Energy Consumption and Carbon Footprint in Automatic Speech Recognition Systems: A Case Study Comparing Whisper and Google Speech-to-Text," *Computer Sciences & Mathematics Forum*, vol. 10, no. 1, p. 6, Jun. 16, 2025. [Online]. Available: https://www.mdpi.com/2813-0324/10/1/6

[16] J. Bhuiyan, "Google undercounts its carbon emissions, report finds," The Guardian, Jul. 2, 2025. [Online]. Available: https://www.theguardian.com/technology/2025/jul/02/google-carbon-emissions-report

[17] K. Robison, "Meta got caught gaming AI benchmarks," The Verge, Apr. 2025. [Online]. Available: https://www.theverge.com/meta/645012/meta-llama-4-maverick-benchmarks-gaming

[18] C.-J. Wu, R. Raghavendra, U. Gupta, B. Acun, N. Ardalani, K. Maeng, G. Chang, F. A. Behram, J. Huang, C. Bai, M. Gschwind, A. Gupta, M. Ott, A. Melnikov, S. Candido, D. Brooks, G. Chauhan, B. Lee, H.-H. S. Lee, B. Akyildiz, M. Balandat, J. Spisak, R. Jain, M. Rabbat and K. Hazelwood, "Sustainable AI: Environmental Implications, Challenges and Opportunities," arXiv preprint arXiv:2111.00364, Jan. 9, 2022. [Online]. Available: https://arxiv.org/abs/2111.00364

[19] Y. Peng et al., "Reproducing Whisper-Style Training Using an Open-Source Toolkit and Publicly Available Data," arXiv:2309.13876v1 [cs.CL], 2023. [Online]. Available: https://arxiv.org/abs/2309.13876v1

[20] NVIDIA Corporation, "NVIDIA A100 40GB PCIe GPU Accelerator Product Brief," NVIDIA, 2020. [Online]. Available: https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/A100-PCIE-Prduct-Brief.pdf

[21] Uptime Institute, "Uptime Institute Global Data Center Survey 2024," UII Keynote Report 146M, 2024. [Online]. Available: https://datacenter.uptimeinstitute.com/rs/711-RIA-145/images/2024.GlobalDataCenterSurvey.Report.pdf

[22] Netrality Data Centers, "High-Density Colocation for AI and GPU Workloads," 2025. [Online]. Available: https://netrality.com/blog/high-density-colocation-ai-gpu-infrastructure/

[23] Microsoft, “Microsoft Teams surpasses 300 million monthly active users,” *Microsoft FY2023 Q3 Earnings Conference Call Transcript*, Apr. 2023. [Online]. Available: https://www.microsoft.com/en-us/investor/events/fy-2023/earnings-fy-2023-q3/ :contentReference[oaicite:0]{index=0}

