"""Collaboration Service API — reviews, diffs, A/B tests — empty until persisted workflow exists."""

from fastapi import APIRouter

from app.domains.collaboration.schemas import CollaborationScreen, DiffPanel

router = APIRouter()


_EMPTY_DIFF = DiffPanel(header="", rows=[])


@router.get("/overview", response_model=CollaborationScreen)
async def get_collaboration_overview() -> CollaborationScreen:
    """Return Collaboration Lab placeholders; backlog items load from persistence later."""
    return CollaborationScreen(
        kpis=[],
        activeReviews=[],
        diff=_EMPTY_DIFF,
        reviewThread=[],
        abTests=[],
        approvalFlow=[],
        footerCards=[],
    )


@router.post("/reviews/{review_id}/approve")
async def approve_review(review_id: str) -> dict[str, str]:
    """Approve a strategy review."""
    return {"review_id": review_id, "status": "approved"}
