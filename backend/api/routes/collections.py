from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_paper_repo
from api.schemas.collection import (
    CollectionListResponse,
    CollectionMutationResponse,
    CreateCollectionRequest,
    FolderInfo,
    RenameCollectionRequest,
)
from src.database.paper_repository import PaperRepository

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=CollectionListResponse)
def list_collections(
    repo: PaperRepository = Depends(get_paper_repo),
):
    """List all collections with paper counts."""
    counts = repo.get_folder_counts()
    all_folders = repo.get_all_folders()

    data = [
        FolderInfo(name=name, count=counts.get(name, 0))
        for name in all_folders
    ]
    return CollectionListResponse(data=data)


@router.post("", response_model=CollectionMutationResponse)
def create_collection(
    body: CreateCollectionRequest,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Create a new empty collection."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")

    # Check uniqueness
    existing = repo.get_all_folders()
    if name in existing:
        raise HTTPException(status_code=409, detail="Collection already exists")

    repo.create_empty_folder(name)
    return CollectionMutationResponse(success=True, message="Collection created")


@router.put("/{folder_name}", response_model=CollectionMutationResponse)
def rename_collection(
    folder_name: str,
    body: RenameCollectionRequest,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Rename a collection."""
    new_name = body.new_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="New name cannot be empty")

    existing = repo.get_all_folders()
    if folder_name not in existing:
        raise HTTPException(status_code=404, detail="Collection not found")
    if new_name in existing and new_name != folder_name:
        raise HTTPException(status_code=409, detail="A collection with this name already exists")

    affected = repo.rename_folder(folder_name, new_name)
    return CollectionMutationResponse(
        success=True,
        message="Collection renamed",
        affected_count=affected,
    )


@router.delete("/{folder_name}", response_model=CollectionMutationResponse)
def delete_collection(
    folder_name: str,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Delete a collection (removes folder from all papers)."""
    existing = repo.get_all_folders()
    if folder_name not in existing:
        raise HTTPException(status_code=404, detail="Collection not found")

    affected = repo.delete_folder(folder_name)
    return CollectionMutationResponse(
        success=True,
        message="Collection deleted",
        affected_count=affected,
    )
