from db.models import Base


def __getattr__(name: str):
    if name in {"SessionLocal", "engine", "get_db"}:
        from db import session

        return getattr(session, name)
    raise AttributeError(name)

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
