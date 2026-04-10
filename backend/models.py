from sqlalchemy import VARCHAR, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False)
    pwd = Column(String(255), nullable=False)
    name = Column(String(50), nullable=False)
    nick = Column(String(50))
    dept = Column(String(50))
    job = Column(String(50))
    profile_img = Column(String(255))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class Correction(Base):
    __tablename__ = "corrections"

    corr_idx = Column(Integer, primary_key=True, index=True)
    id = Column(Integer)
    upload_text = Column(Text)
    upload_vector = Column(Vector(768))
    corr_text = Column(Text)
    aggression_score = Column(Integer, default=0, server_default='0')
    emotion_score = Column(Integer, default=0, server_default='0')
    politeness_score = Column(Integer, default=0, server_default='0')
    tone_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Embeddings(Base):
    __tablename__ = "embeddings"

    ebd_idx = Column(Integer, primary_key=True, index=True)
    original_text = Column(Text, nullable=False)
    corrected_text = Column(Vector(768))
    context_type = Column(VARCHAR(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    corrected_text_raw = Column(Text, nullable=False)