from __future__ import annotations

from typing import List

from pydantic import BaseModel


class FavoriteRequest(BaseModel):
    folder: str


class FolderInfo(BaseModel):
    name: str
    count: int


class CollectionListResponse(BaseModel):
    data: List[FolderInfo]


class CreateCollectionRequest(BaseModel):
    name: str


class RenameCollectionRequest(BaseModel):
    new_name: str


class CollectionMutationResponse(BaseModel):
    success: bool
    message: str
    affected_count: int = 0
