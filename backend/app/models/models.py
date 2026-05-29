import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username   = Column(String(80), unique=True, nullable=False, index=True)
    email      = Column(String(120), unique=True, nullable=True)
    hashed_pw  = Column(String, nullable=False)
    role       = Column(String(20), default="Analyst")
    created_at = Column(DateTime, default=datetime.utcnow)
    datasets   = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", back_populates="owner", cascade="all, delete-orphan")

class Dataset(Base):
    __tablename__ = "datasets"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id    = Column(String, ForeignKey("users.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    filename    = Column(String(200), nullable=False)
    filetype    = Column(String(20))
    file_path   = Column(String(400))
    rows        = Column(Integer)
    columns     = Column(Integer)
    size_bytes  = Column(Integer)
    col_names   = Column(JSON)      # list of column names
    recipe      = Column(JSON)      # cleaning recipe steps
    created_at  = Column(DateTime, default=datetime.utcnow)
    owner       = relationship("User", back_populates="datasets")

class Dashboard(Base):
    __tablename__ = "dashboards"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id    = Column(String, ForeignKey("users.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    dataset_id  = Column(String, nullable=True)
    widgets     = Column(JSON, default=list)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner       = relationship("User", back_populates="dashboards")

class Report(Base):
    __tablename__ = "reports"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id     = Column(String, ForeignKey("users.id"), nullable=False)
    title        = Column(String(200), nullable=False)
    description  = Column(Text, nullable=True)
    dashboard_id = Column(String, nullable=True)
    dataset_id   = Column(String, nullable=True)
    share_token  = Column(String(20), unique=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
