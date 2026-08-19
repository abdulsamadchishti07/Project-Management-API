from enum import Enum


class Role(str, Enum):
    VIEWER = "viewer"
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


# Numerical rank for role hierarchy: Higher number means higher authority
ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.MEMBER: 2,
    Role.ADMIN: 3,
    Role.OWNER: 4,
}


def has_sufficient_role(user_role: str | Role, required_role: str | Role) -> bool:
    """
    Compares the user's role against the required role.
    Returns True if the user's role rank is equal to or higher than the required role rank.

    Examples:
        has_sufficient_role("admin", "member") -> True  (Rank 3 >= Rank 2)
        has_sufficient_role("viewer", "member") -> False (Rank 1 < Rank 2)
        has_sufficient_role("owner", "admin")  -> True  (Rank 4 >= Rank 3)
    """
    try:
        user_r = Role(str(user_role).lower())
        req_r = Role(str(required_role).lower())
    except ValueError:
        return False

    return ROLE_HIERARCHY.get(user_r, 0) >= ROLE_HIERARCHY.get(req_r, 0)
