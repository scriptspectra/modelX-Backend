from sqlmodel import Session, select
from .db import engine, StabilitySnapshot

def save_snapshot_to_db(category_scores: dict, composite: float, top_keywords: list, total_items: int, last_snapshot_path: str):
    """Save a stability snapshot to the database and return the created record as dict."""
    snap = StabilitySnapshot(
        composite_score=float(composite),
        category_scores=category_scores or {},
        top_keywords=top_keywords or [],
        total_items=int(total_items or 0),
        last_snapshot_path=last_snapshot_path,
    )
    with Session(engine) as session:
        session.add(snap)
        session.commit()
        session.refresh(snap)
        # convert to serializable dict
        return {
            "id": snap.id,
            "created_at": snap.created_at.isoformat(),
            "composite_score": snap.composite_score,
            "category_scores": snap.category_scores,
            "top_keywords": snap.top_keywords,
            "total_items": snap.total_items,
            "last_snapshot_path": snap.last_snapshot_path,
        }

def get_recent_snapshots(limit: int = 24):
    """Return recent stability snapshots ordered by created_at desc."""
    with Session(engine) as session:
        stmt = select(StabilitySnapshot).order_by(StabilitySnapshot.created_at.desc()).limit(limit)
        rows = session.exec(stmt).all()
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "composite_score": r.composite_score,
                "category_scores": r.category_scores,
                "top_keywords": r.top_keywords,
                "total_items": r.total_items,
                "last_snapshot_path": r.last_snapshot_path,
            })
        return out
