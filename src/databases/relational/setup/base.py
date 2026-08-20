"""
SQLAlchemy Declarative Base.
"""

# --- IMPORTS ---
from sqlalchemy import TEXT
from sqlalchemy.orm import DeclarativeBase


# --- CODE ---
class BASE(DeclarativeBase):
    """
    Declarative base for every ORM model.
    """

    type_annotation_map = {
        str: TEXT,
    }
