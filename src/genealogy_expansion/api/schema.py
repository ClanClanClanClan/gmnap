from __future__ import annotations

from typing import List

from pydantic import BaseModel


class LineagePath(BaseModel):
    length: int
    nodes: List[str]


class LineageResponse(BaseModel):
    start: str
    depth: int
    paths: List[LineagePath]
