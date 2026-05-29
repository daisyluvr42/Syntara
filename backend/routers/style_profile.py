"""Style profile API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.style_profile import StyleProfileBuildRequest, StyleProfileRevisionRequest, StyleProfileSaveRequest
from backend.services.style_profile import (
    build_style_profile,
    get_style_profile,
    list_style_profiles,
    save_style_profile,
    set_default_style_profile,
    update_style_profile_from_revision,
)

router = APIRouter(prefix="/api/style-profiles", tags=["style-profiles"])


@router.get("")
async def list_profiles(project: str | None = None, style_type: str | None = None):
    return list_style_profiles(project=project, style_type=style_type)


@router.get("/default")
async def get_default_profile(project: str = "default"):
    try:
        return get_style_profile(project=project, default=True)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    try:
        return get_style_profile(profile_id=profile_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/build")
async def build_profile(req: StyleProfileBuildRequest):
    try:
        return await build_style_profile(**req.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Style extraction error: {str(exc)}")


@router.post("/revision")
async def update_profile_from_revision(req: StyleProfileRevisionRequest):
    try:
        return await update_style_profile_from_revision(**req.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Revision style extraction error: {str(exc)}")


@router.post("")
async def save_profile(req: StyleProfileSaveRequest):
    try:
        return save_style_profile(**req.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.put("/{profile_id}/default")
async def set_profile_default(profile_id: str):
    try:
        return set_default_style_profile(profile_id=profile_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
