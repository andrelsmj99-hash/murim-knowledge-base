"""
Novel and Chapter models for the knowledge base.
"""
import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Novel(Base):
    __tablename__ = "novels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), nullable=True)
    genre = Column(String(100), nullable=True)
    source_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String(10), default="en")  # "en", "pt", etc.
    total_chapters = Column(Integer, default=0)
    
    # Relationships
    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('title', 'author', name='uix_novel_title_author'),
    )


class Chapter(Base):
    __tablename__ = "chapters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    novel_id = Column(UUID(as_uuid=True), ForeignKey("novels.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    
    # Relationships
    novel = relationship("Novel", back_populates="chapters")

    __table_args__ = (
        UniqueConstraint('novel_id', 'chapter_number', name='uix_chapter_novel_number'),
    )