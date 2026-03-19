from enum import Enum

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str = Field(default="azure_apim", description="LLM Provider")
    model: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(default=0.0)


class DatasetConfig(BaseModel):
    input_dir: str = Field(default="evals/characteristics/input")


class RunConfig(BaseModel):
    output_dir: str = Field(default="evals/characteristics/output")


class PromptsConfig(BaseModel):
    extraction_template: str = Field(default="evals/characteristics/prompts/characteristic_extraction.jinja2")


class EvalsConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)


class CharacteristicCategory(str, Enum):
    AGE = "Age"
    DISABILITY = "Disability"
    ETHNICITY = "Ethnicity"
    LOCATION = "Location"
    MARRIAGE_STATUS = "Marriage and Relationship Status"
    PREGNANCY_MATERNITY = "Pregnancy and Maternity"
    RACE = "Race"
    RELIGION = "Religion"
    SEX = "Sex"
    SEX_GENDER = "Sex and Gender"
    SEXUALITY = "Sexuality"


class TextSpan(BaseModel):
    start_index: int | None = Field(None, description="Start index of the span")
    end_index: int | None = Field(None, description="End index of the span")
    text: str = Field(..., description="The exact substring from the transcript")


class CharacteristicDetection(BaseModel):
    characteristic: CharacteristicCategory = Field(..., description="The characteristic")
    attribute_value: str = Field(..., description="The value (e.g., 'Female', 'Muslim', 'Elderly')")
    evidence_spans: list[TextSpan] = Field(default_factory=list)


class CharacteristicExtractionOutput(BaseModel):
    version: str = Field(default="1.1")
    detected_characteristics: list[CharacteristicDetection]
