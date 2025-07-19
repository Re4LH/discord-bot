"""
Database models for the Discord Availability Poll Bot
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import os

Base = declarative_base()

class ServerConfig(Base):
    """Server configuration table"""
    __tablename__ = 'server_configs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String(50), unique=True, nullable=False)
    enabled = Column(Boolean, default=False)
    channel_id = Column(String(50), nullable=True)
    poll_hour = Column(Integer, default=5)  # 5 AM UTC
    poll_minute = Column(Integer, default=0)
    timezone = Column(String(50), default='UTC')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    polls = relationship("Poll", back_populates="server", cascade="all, delete-orphan")
    poll_options = relationship("PollOption", back_populates="server", cascade="all, delete-orphan")

class PollOption(Base):
    """Poll options for each server"""
    __tablename__ = 'poll_options'
    
    id = Column(Integer, primary_key=True)
    server_config_id = Column(Integer, ForeignKey('server_configs.id'))
    emoji = Column(String(10), nullable=False)
    text = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("ServerConfig", back_populates="poll_options")

class Poll(Base):
    """Individual poll instances"""
    __tablename__ = 'polls'
    
    id = Column(Integer, primary_key=True)
    server_config_id = Column(Integer, ForeignKey('server_configs.id'))
    guild_id = Column(String(50), nullable=False)
    channel_id = Column(String(50), nullable=False)
    message_id = Column(String(50), unique=True, nullable=False)
    poll_date = Column(String(100), nullable=False)  # "утре понedelник, 20 юли 2025"
    is_test = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("ServerConfig", back_populates="polls")
    votes = relationship("Vote", back_populates="poll", cascade="all, delete-orphan")

class Vote(Base):
    """Individual votes on polls"""
    __tablename__ = 'votes'
    
    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey('polls.id'))
    user_id = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    emoji = Column(String(10), nullable=False)
    voted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    poll = relationship("Poll", back_populates="votes")

# Database setup
def get_database_url():
    """Get database URL from environment"""
    return os.getenv('DATABASE_URL')

def create_database_engine():
    """Create database engine"""
    database_url = get_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Handle both postgres:// and postgresql:// URLs
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url, echo=False)
    return engine

def create_tables():
    """Create all database tables"""
    engine = create_database_engine()
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session"""
    engine = create_database_engine()
    Session = sessionmaker(bind=engine)
    return Session()