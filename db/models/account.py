from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Enum, func, ForeignKey
from sqlalchemy.orm import relationship
from db.models.base import Base
import enum


class AccountStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    HIDDEN = "HIDDEN"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="UZS")
    description = Column(Text, nullable=True)
    status = Column(Enum(AccountStatus),
                    default=AccountStatus.DRAFT, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    media = relationship(
        "AccountMedia", back_populates="account", cascade="all, delete-orphan")
    credentials = relationship(
        "Credential", back_populates="account", uselist=False, cascade="all, delete-orphan")


class AccountMedia(Base):
    __tablename__ = "account_media"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey(
        "accounts.id", ondelete="CASCADE"), nullable=False)
    media_type = Column(String(50), nullable=False)  # photo or video
    file_id = Column(String(255), nullable=False)
    order_index = Column(Integer, default=0)

    account = relationship("Account", back_populates="media")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey(
        "accounts.id", ondelete="CASCADE"), unique=True, nullable=False)
    login_info = Column(Text, nullable=False)  # Encrypted
    password_info = Column(Text, nullable=False)  # Encrypted

    account = relationship("Account", back_populates="credentials")
