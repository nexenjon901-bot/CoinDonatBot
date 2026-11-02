from sqlalchemy import Column, Integer, ForeignKey
from db.models.base import Base


class Favorite(Base):
    __tablename__ = "favorites"

    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), primary_key=True)
    account_id = Column(Integer, ForeignKey(
        "accounts.id", ondelete="CASCADE"), primary_key=True)
