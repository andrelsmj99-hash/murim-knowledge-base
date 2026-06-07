"""
Location models for the knowledge base.
"""
import uuid

from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base
from .character import character_locations


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), index=True, nullable=False)
    type = Column(String(100), nullable=False)  # e.g., "City", "Mountain", "Sect Grounds", "Village"
    description = Column(Text, nullable=True)
    region = Column(String(255), nullable=True)
    realm = Column(String(255), nullable=True)  # For kingdoms/empires
    parent_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)

    # Self-referential hierarchy
    parent_location = relationship("Location", remote_side=[id], back_populates="sub_locations")
    sub_locations = relationship("Location", back_populates="parent_location")

    # Many-to-many with Character (via association table)
    characters = relationship("Character", secondary=character_locations, back_populates="locations")

    # One location can be HQ of many organizations (one-to-many)
    organizations = relationship("Organization", back_populates="headquarters")

    __table_args__ = (
        UniqueConstraint("name", "type", name="uix_location_name_type"),
    )
