"""Minimal probe for the Q1/L1 Python-arm typing configuration."""

from pydantic import BaseModel, ConfigDict


class ProbeModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    value: int


def probe_value(model: ProbeModel) -> int:
    return model.value
