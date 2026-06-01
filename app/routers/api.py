from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Optional

from app.database import get_db
from app.models import Following, Snapshot, SnapshotDiff
from app.schemas import (
    FollowingOut, SnapshotOut, SnapshotDiffOut,
    DashboardStats, FeedItem
)

router = APIRouter(prefix="/api")


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    total = db.query(Following).filter(Following.is_active == True).count()
    last_scan_row = db.query(func.max(Snapshot.timestamp)).scalar()
    total_scans = db.query(Snapshot).count()

    def count_diffs(since: datetime, diff_type: str) -> int:
        return (
            db.query(SnapshotDiff)
            .filter(
                and_(SnapshotDiff.diff_type == diff_type, SnapshotDiff.timestamp >= since)
            )
            .count()
        )

    # Segment distribution
    segments = {}
    rows = (
        db.query(Following.segment, func.count(Following.id))
        .filter(Following.is_active == True)
        .group_by(Following.segment)
        .all()
    )
    for seg, cnt in rows:
        segments[seg or "Segmento Ambiguo"] = cnt

    return DashboardStats(
        total_following=total,
        added_last_24h=count_diffs(last_24h, "added"),
        removed_last_24h=count_diffs(last_24h, "removed"),
        added_last_7d=count_diffs(last_7d, "added"),
        removed_last_7d=count_diffs(last_7d, "removed"),
        last_scan=last_scan_row,
        total_scans=total_scans,
        segments=segments,
    )


@router.get("/feed", response_model=List[FeedItem])
def get_feed(
    limit: int = Query(50, le=200),
    offset: int = 0,
    diff_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(SnapshotDiff)
        .options(joinedload(SnapshotDiff.following))
        .order_by(SnapshotDiff.timestamp.desc())
    )
    if diff_type in ("added", "removed"):
        q = q.filter(SnapshotDiff.diff_type == diff_type)

    diffs = q.offset(offset).limit(limit).all()

    result = []
    for d in diffs:
        f = d.following
        result.append(
            FeedItem(
                diff_type=d.diff_type,
                timestamp=d.timestamp,
                username=d.following_username,
                full_name=f.full_name if f else None,
                profile_pic_url=f.profile_pic_url if f else None,
                segment=f.segment if f else None,
            )
        )
    return result


@router.get("/followings", response_model=List[FollowingOut])
def list_followings(
    limit: int = Query(50, le=500),
    offset: int = 0,
    search: Optional[str] = None,
    segment: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
):
    q = db.query(Following)

    if is_active is not None:
        q = q.filter(Following.is_active == is_active)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            Following.username.ilike(pattern) | Following.full_name.ilike(pattern)
        )
    if segment:
        q = q.filter(Following.segment == segment)

    return q.order_by(Following.last_seen.desc()).offset(offset).limit(limit).all()


@router.get("/snapshots", response_model=List[SnapshotOut])
def list_snapshots(
    limit: int = Query(30, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return (
        db.query(Snapshot)
        .order_by(Snapshot.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/snapshots/{snapshot_id}/diffs", response_model=List[SnapshotDiffOut])
def get_snapshot_diffs(snapshot_id: int, db: Session = Depends(get_db)):
    snap = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return (
        db.query(SnapshotDiff)
        .options(joinedload(SnapshotDiff.following))
        .filter(SnapshotDiff.snapshot_id == snapshot_id)
        .all()
    )


@router.get("/growth")
def get_growth_chart(days: int = Query(30, le=365), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.timestamp >= since)
        .order_by(Snapshot.timestamp.asc())
        .all()
    )
    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "total_count": s.total_count,
            "added": s.added_count,
            "removed": s.removed_count,
        }
        for s in snapshots
    ]
