"""
Organization models for the knowledge base.
"""

import uuid

from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base
from .character import character_organizations


class OrganizationRelationship(Base):
    """Directional relationship between two organizations (rival / ally / subordinate)."""

    __tablename__ = "organization_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    related_organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type = Column(
        String(100), nullable=False
    )  # "rival", "ally", "subordinate", "parent"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "related_organization_id",
            "relationship_type",
            name="uix_org_relationship",
        ),
    )


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), index=True, nullable=False)
    type = Column(String(100), nullable=False)  # e.g., "Sect", "Clan", "Guild", "Alliance", "Cult"
    description = Column(Text, nullable=True)

    # Hierarchical parent/child (single parent)
    parent_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    parent_org = relationship("Organization", remote_side=[id], back_populates="subsidiaries")
    subsidiaries = relationship("Organization", back_populates="parent_org")

    # Headquarters (FK to a single Location)
    headquarters_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    headquarters = relationship("Location", back_populates="organizations")

    # Many-to-many with Character (via association table)
    members = relationship(
        "Character", secondary=character_organizations, back_populates="organizations"
    )

    # Filtered relationships by type
    rivals = relationship(
        "Organization",
        secondary="organization_relationships",
        primaryjoin="and_(Organization.id==OrganizationRelationship.organization_id, "
        "OrganizationRelationship.relationship_type=='rival')",
        secondaryjoin="Organization.id==OrganizationRelationship.related_organization_id",
        viewonly=True,
    )

    allies = relationship(
        "Organization",
        secondary="organization_relationships",
        primaryjoin="and_(Organization.id==OrganizationRelationship.organization_id, "
        "OrganizationRelationship.relationship_type=='ally')",
        secondaryjoin="Organization.id==OrganizationRelationship.related_organization_id",
        viewonly=True,
    )

    __table_args__ = (UniqueConstraint("name", "type", name="uix_org_name_type"),)
