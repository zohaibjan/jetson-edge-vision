from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class BoundingBox(StrictModel):
    left: float = Field(ge=0, le=32768)
    top: float = Field(ge=0, le=32768)
    width: float = Field(gt=0, le=32768)
    height: float = Field(gt=0, le=32768)

class Detection(StrictModel):
    class_id: int = Field(ge=0, le=999)
    label: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0, le=1)
    bbox: BoundingBox

class FrameEvent(StrictModel):
    schema_version: Literal["edge.detections.v1"] = Field(alias="schema")
    source_id: str = Field(min_length=1, max_length=64, pattern=r"^[\w.-]+$")
    frame_id: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    width: int = Field(gt=0, le=32768)
    height: int = Field(gt=0, le=32768)
    simulated: bool
    objects: list[Detection] = Field(max_length=128)
