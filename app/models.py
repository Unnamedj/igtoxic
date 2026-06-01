from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TargetProfile(Base):
    __tablename__ = "target_profile"
    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    full_name = Column(String(200), nullable=True)
    profile_pic_url = Column(Text, nullable=True)
    biography = Column(Text, nullable=True)
    followers_count = Column(Integer, nullable=True)
    is_verified = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Following(Base):
    __tablename__ = "followings"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    profile_pic_url = Column(Text, nullable=True)
    segment = Column(String(50), nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    diffs = relationship("SnapshotDiff", back_populates="following", foreign_keys="SnapshotDiff.following_username")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_count = Column(Integer, nullable=False)
    added_count = Column(Integer, default=0)
    removed_count = Column(Integer, default=0)
    scan_duration_seconds = Column(Integer, nullable=True)

    diffs = relationship("SnapshotDiff", back_populates="snapshot")


class SnapshotDiff(Base):
    __tablename__ = "snapshot_diffs"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    following_username = Column(String(100), ForeignKey("followings.username"), nullable=False)
    diff_type = Column(String(10), nullable=False)  # "added" or "removed"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    snapshot = relationship("Snapshot", back_populates="diffs")
    following = relationship("Following", back_populates="diffs", foreign_keys=[following_username])
