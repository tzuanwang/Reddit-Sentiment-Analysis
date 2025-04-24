# backend/utils/serializers.py

from pydantic import BaseModel
from typing import List, Optional

class CommentSerializer(BaseModel):
    id: str
    body: str
    created_utc: int

    class Config:
        orm_mode = True


class PredictionSerializer(BaseModel):
    id: int
    emotion: str
    score: float
    created_utc: int

    class Config:
        orm_mode = True


class PostSerializer(BaseModel):
    id: str
    title: str
    created_utc: int
    comments: List[CommentSerializer] = []
    predictions: List[PredictionSerializer] = []

    class Config:
        orm_mode = True


class HarvestResponse(BaseModel):
    harvested: int
    message: Optional[str] = None
