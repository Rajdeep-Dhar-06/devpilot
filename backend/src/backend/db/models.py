from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from backend.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)   # Application's internal User ID
    
    github_id: Mapped[int] = mapped_column(             # User's unique Github Account ID
        BigInteger,
        unique=True,
        index=True
    )
    login: Mapped[str] = mapped_column(String(39))      # User's current Github Username
    avatar_url: Mapped[str | None] = mapped_column(     # User's profile picture URL
        String(500),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(       # Record creation time
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
class Installation(Base):
    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    github_installation_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
    )

    account_id: Mapped[int] = mapped_column(BigInteger)
    account_login: Mapped[str] = mapped_column(String(255))

    repository_selection: Mapped[str] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)

    github_repo_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
    )

    installation_id: Mapped[int] = mapped_column(
        ForeignKey("installations.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(255))
    private: Mapped[bool] = mapped_column(Boolean)
    html_url: Mapped[str] = mapped_column(String(2048))

    default_branch: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )