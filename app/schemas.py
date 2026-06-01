from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class FollowingOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    profile_pic_url: Optional[str]
    segment: Optional[str]
    first_seen: datetime
    last_seen: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SnapshotDiffOut(BaseModel):
    id: int
    snapshot_id: int
    following_username: str
    diff_type: str
    timestamp: datetime
    following: Optional[FollowingOut]

    class Config:
        from_attributes = True


class SnapshotOut(BaseModel):
    id: int
    timestamp: datetime
    total_count: int
    added_count: int
    removed_count: int
    scan_duration_seconds: Optional[int]

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_following: int
    added_last_24h: int
    removed_last_24h: int
    added_last_7d: int
    removed_last_7d: int
    last_scan: Optional[datetime]
    total_scans: int
    segments: dict


class FeedItem(BaseModel):
    diff_type: str  # "added" or "removed"
    timestamp: datetime
    username: str
    full_name: Optional[str]
    profile_pic_url: Optional[str]
    segment: Optional[str]
