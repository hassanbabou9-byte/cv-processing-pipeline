import uuid


def new_uuid() -> uuid.UUID:
    """Generate a normal random UUID v4."""
    return uuid.uuid4()


def new_uuid_str() -> str:
    """Generate a normal random UUID v4 as a string."""
    return str(uuid.uuid4())


def short_uuid_slice(length: int = 8) -> str:
    """Generate a short UUID fragment."""
    return uuid.uuid4().hex[:length]


def collaborateur_uuid(sequence: int) -> uuid.UUID:
    """
    Generate the required Collaborateur UUID.

    Example:
        1 -> a1000001-0000-0000-0000-000000000001
        2 -> a1000001-0000-0000-0000-000000000002
    """

    if sequence < 1:
        raise ValueError(
            "Collaborateur UUID sequence must be >= 1."
        )

    if sequence > 0xFFFFFFFFFFFF:
        raise ValueError(
            "Collaborateur UUID sequence is too large."
        )

    return uuid.UUID(
        f"a1000001-0000-0000-0000-{sequence:012x}"
    )