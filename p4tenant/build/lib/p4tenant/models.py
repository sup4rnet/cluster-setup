"""Pydantic models for input validation."""

import re
from typing import Optional

from pydantic import BaseModel, field_validator


class TenantInput(BaseModel):
    """Validated tenant input."""

    username: str
    email: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        v = v.strip().lower()

        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 16:
            raise ValueError("Username must be at most 16 characters")

        if not re.match(r"^[a-z][a-z0-9_-]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only "
                "lowercase letters, numbers, underscores, or hyphens"
            )

        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None or v.strip() == "":
            return None

        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")

        return v


class IPAllocation(BaseModel):
    """Represents an IP allocation for a tenant."""

    ip1: str  # e.g., "10.10.0.21/24"
    ip2: str  # e.g., "10.10.0.22/24"

    @property
    def ip1_bare(self) -> str:
        """Get IP1 without subnet mask."""
        return self.ip1.split("/")[0]

    @property
    def ip2_bare(self) -> str:
        """Get IP2 without subnet mask."""
        return self.ip2.split("/")[0]


class TenantInfo(BaseModel):
    """Information about an existing tenant."""

    username: str
    vm_name: str
    ips: list[str]
    in_restart_users: bool
    in_vms_list: bool
    in_inventory: bool
    has_host_vars: bool
