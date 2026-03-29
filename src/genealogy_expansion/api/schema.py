from __future__ import annotations
from pydantic import BaseModel
from typing import List


class LineagePath(BaseModel):
    length: int
    nodes: List[str]


class LineageResponse(BaseModel):
    start: str
    depth: int
    paths: List[LineagePath]
