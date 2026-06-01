from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import time

from app.models import Following, Snapshot, SnapshotDiff, TargetProfile
from app.services.segmentation import classify_segment


def process_scan(db: Session, scraped_users: List[Dict], total_count: int, duration: int, profile_data: Optional[Dict] = None) -> Snapshot:
    """
    Compare scraped_users against current DB state.
    Returns a new Snapshot with diffs recorded.
    scraped_users: list of dicts with keys: username, full_name, profile_pic_url
    """
    scraped_map = {u["username"]: u for u in scraped_users}
    scraped_set: Set[str] = set(scraped_map.keys())

    # Current active followings in DB
    active_followings = db.query(Following).filter(Following.is_active == True).all()
    active_set: Set[str] = {f.username for f in active_followings}

    added_usernames = scraped_set - active_set
    removed_usernames = active_set - scraped_set

    # Create snapshot
    snapshot = Snapshot(
        timestamp=datetime.utcnow(),
        total_count=total_count,
        added_count=len(added_usernames),
        removed_count=len(removed_usernames),
        scan_duration_seconds=duration,
    )
    db.add(snapshot)
    db.flush()  # get snapshot.id

    now = datetime.utcnow()

    # Process additions
    for username in added_usernames:
        user_data = scraped_map[username]
        existing = db.query(Following).filter(Following.username == username).first()

        if existing:
            existing.is_active = True
            existing.last_seen = now
            existing.full_name = user_data.get("full_name") or existing.full_name
            existing.profile_pic_url = user_data.get("profile_pic_url") or existing.profile_pic_url
        else:
            full_name = user_data.get("full_name", "")
            new_following = Following(
                username=username,
                full_name=full_name,
                profile_pic_url=user_data.get("profile_pic_url"),
                segment=classify_segment(full_name),
                first_seen=now,
                last_seen=now,
                is_active=True,
            )
            db.add(new_following)

        diff = SnapshotDiff(
            snapshot_id=snapshot.id,
            following_username=username,
            diff_type="added",
            timestamp=now,
        )
        db.add(diff)

    # Process removals
    for username in removed_usernames:
        following = db.query(Following).filter(Following.username == username).first()
        if following:
            following.is_active = False
            following.last_seen = now

        diff = SnapshotDiff(
            snapshot_id=snapshot.id,
            following_username=username,
            diff_type="removed",
            timestamp=now,
        )
        db.add(diff)

    # Update last_seen for unchanged active followings
    unchanged = active_set & scraped_set
    for username in unchanged:
        db.query(Following).filter(Following.username == username).update(
            {"last_seen": now}
        )

    # Upsert target profile info
    if profile_data:
        existing = db.query(TargetProfile).first()
        if existing:
            for k, v in profile_data.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
        else:
            db.add(TargetProfile(**profile_data, updated_at=datetime.utcnow()))

    db.commit()
    db.refresh(snapshot)
    return snapshot
