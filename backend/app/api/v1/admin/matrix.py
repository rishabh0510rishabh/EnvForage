"""
Admin REST API Endpoints for matrix CRUD operations.
Requires X-Admin-API-Key authentication.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DB, require_admin
from app.compatibility.resolver import clear_compatibility_cache
from app.models.matrix import (
    CUDAMatrixEntry,
    PythonMatrixEntry,
    RocmMatrixEntry,
)
from app.schemas.matrix import (
    CUDAMatrixCreate,
    CUDAMatrixResponse,
    CUDAMatrixUpdate,
    PythonMatrixCreate,
    PythonMatrixResponse,
    PythonMatrixUpdate,
    RocmMatrixCreate,
    RocmMatrixResponse,
    RocmMatrixUpdate,
)

router = APIRouter(
    prefix="/admin/matrix",
    tags=["Admin Matrix"],
    dependencies=[Depends(require_admin)],
)


# ── CUDA Matrix CRUD ─────────────────────────────────────────────────────────


@router.post(
    "/cuda",
    response_model=CUDAMatrixResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a CUDA compatibility matrix entry",
)
async def create_cuda_entry(data: CUDAMatrixCreate, db: DB) -> Any:
    existing = await db.execute(
        select(CUDAMatrixEntry).where(CUDAMatrixEntry.cuda_version == data.cuda_version)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CUDA version already exists in matrix.",
        )

    db_entry = CUDAMatrixEntry(id=uuid.uuid4(), **data.model_dump())
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    await clear_compatibility_cache()
    return db_entry


@router.put(
    "/cuda/{id}",
    response_model=CUDAMatrixResponse,
    summary="Update a CUDA compatibility matrix entry",
)
async def update_cuda_entry(id: uuid.UUID, data: CUDAMatrixUpdate, db: DB) -> Any:
    db_entry = await db.get(CUDAMatrixEntry, id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CUDA matrix entry not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "cuda_version" in update_data:
        existing = await db.execute(
            select(CUDAMatrixEntry).where(
                (CUDAMatrixEntry.cuda_version == update_data["cuda_version"])
                & (CUDAMatrixEntry.id != id)
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CUDA version already exists in matrix.",
            )

    for key, val in update_data.items():
        setattr(db_entry, key, val)

    await db.commit()
    await db.refresh(db_entry)
    await clear_compatibility_cache()
    return db_entry


@router.delete(
    "/cuda/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a CUDA compatibility matrix entry",
)
async def delete_cuda_entry(id: uuid.UUID, db: DB) -> None:
    db_entry = await db.get(CUDAMatrixEntry, id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CUDA matrix entry not found.",
        )

    await db.delete(db_entry)
    await db.commit()
    await clear_compatibility_cache()


# ── ROCm Matrix CRUD ─────────────────────────────────────────────────────────


@router.post(
    "/rocm",
    response_model=RocmMatrixResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ROCm compatibility matrix entry",
)
async def create_rocm_entry(data: RocmMatrixCreate, db: DB) -> Any:
    existing = await db.execute(
        select(RocmMatrixEntry).where(RocmMatrixEntry.rocm_version == data.rocm_version)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ROCm version already exists in matrix.",
        )

    db_entry = RocmMatrixEntry(id=uuid.uuid4(), **data.model_dump())
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    await clear_compatibility_cache()
    return db_entry


@router.put(
    "/rocm/{id}",
    response_model=RocmMatrixResponse,
    summary="Update a ROCm compatibility matrix entry",
)
async def update_rocm_entry(id: uuid.UUID, data: RocmMatrixUpdate, db: DB) -> Any:
    db_entry = await db.get(RocmMatrixEntry, id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ROCm matrix entry not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "rocm_version" in update_data:
        existing = await db.execute(
            select(RocmMatrixEntry).where(
                (RocmMatrixEntry.rocm_version == update_data["rocm_version"])
                & (RocmMatrixEntry.id != id)
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ROCm version already exists in matrix.",
            )

    for key, val in update_data.items():
        setattr(db_entry, key, val)

    await db.commit()
    await db.refresh(db_entry)
    await clear_compatibility_cache()
    return db_entry


@router.delete(
    "/rocm/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ROCm compatibility matrix entry",
)
async def delete_rocm_entry(id: uuid.UUID, db: DB) -> None:
    db_entry = await db.get(RocmMatrixEntry, id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ROCm matrix entry not found.",
        )

    await db.delete(db_entry)
    await db.commit()
    await clear_compatibility_cache()


# ── Python/Framework Matrix CRUD ─────────────────────────────────────────────


@router.post(
    "/python",
    response_model=PythonMatrixResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Python/Framework compatibility matrix entry",
)
async def create_python_entry(data: PythonMatrixCreate, db: DB) -> Any:
    existing = await db.execute(
        select(PythonMatrixEntry).where(
            (PythonMatrixEntry.framework == data.framework)
            & (PythonMatrixEntry.version == data.version)
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Python matrix entry for this framework and version already exists.",
        )

    db_entry = PythonMatrixEntry(id=uuid.uuid4(), **data.model_dump())
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    await clear_compatibility_cache()
    return db_entry


@router.put(
    "/python/{id}",
    response_model=PythonMatrixResponse,
    summary="Update a Python/Framework compatibility matrix entry",
)
async def update_python_entry(id: uuid.UUID, data: PythonMatrixUpdate, db: DB) -> Any:
    db_entry = await db.get(PythonMatrixEntry, id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Python matrix entry not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "framework" in update_data or "version" in update_data:
        new_framework = update_data.get("framework", db_entry.framework)
        new_version = update_data.get("version", db_entry.version)
        existing = await db.execute(
            select(PythonMatrixEntry).where(
                (PythonMatrixEntry.framework == new_framework)
                & (PythonMatrixEntry.version == new_version)
                & (PythonMatrixEntry.id != id)
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Python matrix entry for this framework and version already exists.",
            )

    for key, val in update_data.items():
        setattr(db_entry, key, val)

    await db.commit()
    await db.refresh(db_entry)
    await clear_compatibility_cache()
    return db_entry


@router.delete(
    "/python/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Python/Framework compatibility matrix entry",
)
async def delete_python_entry(id: uuid.UUID, db: DB) -> None:
    db_entry = await db.get(PythonMatrixEntry, id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Python matrix entry not found.",
        )

    await db.delete(db_entry)
    await db.commit()
    await clear_compatibility_cache()
