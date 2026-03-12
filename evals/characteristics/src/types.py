from pydantic import BaseModel, Field


class TextSpan(BaseModel):
    start_index: int | None = Field(description="Start index of the span in the transcript (if available)")
    end_index: int | None = Field(description="End index of the span in the transcript (if available)")
    text: str = Field(description="Exact span of text in the transcript indicating the characteristic")


class CharacteristicDetection(BaseModel):
    characteristic: str = Field(description="The category, e.g., 'Race', 'Age', 'Religion', 'Disability', 'Sex/Gender'")
    attribute_value: str = Field(description="The specific value extracted, e.g., 'Asian', '65 years old', 'Female'")
    evidence_spans: list[TextSpan] = Field(description="Passages in the transcript indicating this characteristic")


class CharacteristicExtractionOutput(BaseModel):
    version: str = Field(default="1.0", description="Version of the data contract")
    detected_characteristics: list[CharacteristicDetection] = Field(
        description="List of all characteristics identified"
    )
