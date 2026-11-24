"""
ManutCar Shared Schemas Package
Pydantic v2 models for API contracts, validation, and serialization.
Shared between Backend (FastAPI) and Frontend (via code generation or manual sync).
"""

from .webhook import (
    ClerkWebhookPayload,
    ClerkUserData,
    ClerkOrganizationData,
    ClerkOrganizationMembershipData,
)

__version__ = "0.1.0"

__all__ = [
    "ClerkWebhookPayload",
    "ClerkUserData",
    "ClerkOrganizationData",
    "ClerkOrganizationMembershipData",
]
