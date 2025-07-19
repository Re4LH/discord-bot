"""
Database manager for Discord Poll Bot
Handles all database operations and migrations from JSON to PostgreSQL
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from database.models import (
    Base, ServerConfig, PollOption, Poll, Vote, 
    create_database_engine, create_tables, get_session
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for the Discord Poll Bot"""
    
    def __init__(self):
        """Initialize database manager"""
        self.engine = None
        self.Session = None
        self._setup_database()
    
    def _setup_database(self):
        """Setup database connection and create tables"""
        try:
            self.engine = create_database_engine()
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database setup completed successfully")
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise
    
    def migrate_from_json(self, json_file_path: str = "config/servers.json"):
        """Migrate existing JSON configuration to database"""
        try:
            # Load existing JSON data
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                logger.info(f"Loaded JSON data from {json_file_path}")
            except FileNotFoundError:
                logger.info("No existing JSON file found, starting fresh")
                return
            except Exception as e:
                logger.error(f"Failed to load JSON file: {e}")
                return
            
            session = self.Session()
            try:
                # Migrate each server configuration
                for guild_id, config in json_data.items():
                    # Check if server already exists
                    existing = session.query(ServerConfig).filter_by(guild_id=guild_id).first()
                    if existing:
                        logger.info(f"Server {guild_id} already exists in database, skipping")
                        continue
                    
                    # Create server config
                    server = ServerConfig(
                        guild_id=guild_id,
                        enabled=config.get('enabled', False),
                        channel_id=config.get('channel_id'),
                        poll_hour=config.get('poll_hour', 5),
                        poll_minute=config.get('poll_minute', 0),
                        timezone=config.get('timezone', 'UTC')
                    )
                    session.add(server)
                    session.flush()  # Get the ID
                    
                    # Add poll options
                    poll_options = config.get('poll_options', [
                        "✅ Свободен цял ден",
                        "🌅 Свободен сутрин (9:00 - 12:00)",
                        "☀️ Свободен следобед (12:00 - 18:00)",
                        "🌙 Свободен вечер (18:00 - 23:00)",
                        "🌃 Свободен късно вечер (23:00+)",
                        "🤔 Не съм сигурен",
                        "❌ Не съм свободен"
                    ])
                    
                    emojis = ["✅", "🌅", "☀️", "🌙", "🌃", "🤔", "❌"]
                    
                    for i, option_text in enumerate(poll_options[:7]):
                        option = PollOption(
                            server_config_id=server.id,
                            emoji=emojis[i],
                            text=option_text,
                            order_index=i
                        )
                        session.add(option)
                    
                    logger.info(f"Migrated server {guild_id} to database")
                
                session.commit()
                logger.info("JSON migration completed successfully")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to migrate JSON data: {e}")
                raise
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    def get_server_config(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get server configuration from database"""
        session = self.Session()
        try:
            server = session.query(ServerConfig).filter_by(guild_id=str(guild_id)).first()
            if not server:
                return None
            
            # Get poll options
            options = session.query(PollOption).filter_by(
                server_config_id=server.id
            ).order_by(PollOption.order_index).all()
            
            config = {
                'enabled': server.enabled,
                'channel_id': server.channel_id,
                'poll_hour': server.poll_hour,
                'poll_minute': server.poll_minute,
                'timezone': server.timezone,
                'poll_options': [opt.text for opt in options],
                'poll_emojis': [opt.emoji for opt in options],
                'poll_history': []  # Will be populated from Poll table
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get server config for {guild_id}: {e}")
            return None
        finally:
            session.close()
    
    def save_server_config(self, guild_id: str, config: Dict[str, Any]):
        """Save server configuration to database"""
        session = self.Session()
        try:
            guild_id = str(guild_id)
            
            # Get or create server
            server = session.query(ServerConfig).filter_by(guild_id=guild_id).first()
            if not server:
                server = ServerConfig(guild_id=guild_id)
                session.add(server)
                session.flush()
            
            # Update server config
            server.enabled = config.get('enabled', False)
            server.channel_id = config.get('channel_id')
            server.poll_hour = config.get('poll_hour', 5)
            server.poll_minute = config.get('poll_minute', 0)
            server.timezone = config.get('timezone', 'UTC')
            server.updated_at = datetime.utcnow()
            
            # Update poll options if provided
            if 'poll_options' in config:
                # Remove existing options
                session.query(PollOption).filter_by(server_config_id=server.id).delete()
                
                # Add new options
                poll_options = config['poll_options']
                emojis = config.get('poll_emojis', ["✅", "🌅", "☀️", "🌙", "🌃", "🤔", "❌"])
                
                for i, option_text in enumerate(poll_options[:7]):
                    option = PollOption(
                        server_config_id=server.id,
                        emoji=emojis[i] if i < len(emojis) else "❓",
                        text=option_text,
                        order_index=i
                    )
                    session.add(option)
            
            session.commit()
            logger.debug(f"Saved config for server {guild_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save server config for {guild_id}: {e}")
            raise
        finally:
            session.close()
    
    def create_poll(self, guild_id: str, channel_id: str, message_id: str, 
                   poll_date: str, is_test: bool = False) -> int:
        """Create a new poll record"""
        session = self.Session()
        try:
            server = session.query(ServerConfig).filter_by(guild_id=str(guild_id)).first()
            if not server:
                raise ValueError(f"Server {guild_id} not found in database")
            
            poll = Poll(
                server_config_id=server.id,
                guild_id=str(guild_id),
                channel_id=str(channel_id),
                message_id=str(message_id),
                poll_date=poll_date,
                is_test=is_test
            )
            
            session.add(poll)
            session.commit()
            
            # Cleanup old polls (keep only last 3)
            old_polls = session.query(Poll).filter_by(
                server_config_id=server.id
            ).order_by(Poll.created_at.desc()).offset(3).all()
            
            for old_poll in old_polls:
                session.delete(old_poll)
            
            session.commit()
            
            logger.info(f"Created poll {message_id} for server {guild_id}")
            return poll.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create poll: {e}")
            raise
        finally:
            session.close()
    
    def save_vote(self, message_id: str, user_id: str, username: str, 
                  display_name: str, emoji: str):
        """Save or update a vote"""
        session = self.Session()
        try:
            # Find the poll
            poll = session.query(Poll).filter_by(message_id=str(message_id)).first()
            if not poll:
                logger.warning(f"Poll not found for message {message_id}")
                return
            
            # Check for existing vote by this user
            existing_vote = session.query(Vote).filter_by(
                poll_id=poll.id,
                user_id=str(user_id)
            ).first()
            
            if existing_vote:
                # Update existing vote
                existing_vote.emoji = emoji
                existing_vote.updated_at = datetime.utcnow()
                existing_vote.display_name = display_name  # Update display name
                logger.debug(f"Updated vote for user {user_id} in poll {message_id}")
            else:
                # Create new vote
                vote = Vote(
                    poll_id=poll.id,
                    user_id=str(user_id),
                    username=username,
                    display_name=display_name,
                    emoji=emoji
                )
                session.add(vote)
                logger.debug(f"Created new vote for user {user_id} in poll {message_id}")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save vote: {e}")
            raise
        finally:
            session.close()
    
    def remove_vote(self, message_id: str, user_id: str):
        """Remove a user's vote from a poll"""
        session = self.Session()
        try:
            poll = session.query(Poll).filter_by(message_id=str(message_id)).first()
            if not poll:
                return
            
            vote = session.query(Vote).filter_by(
                poll_id=poll.id,
                user_id=str(user_id)
            ).first()
            
            if vote:
                session.delete(vote)
                session.commit()
                logger.debug(f"Removed vote for user {user_id} from poll {message_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to remove vote: {e}")
        finally:
            session.close()
    
    def get_poll_votes(self, message_id: str) -> Dict[str, List[str]]:
        """Get all votes for a poll organized by emoji"""
        session = self.Session()
        try:
            poll = session.query(Poll).filter_by(message_id=str(message_id)).first()
            if not poll:
                return {}
            
            votes = session.query(Vote).filter_by(poll_id=poll.id).all()
            
            # Organize votes by emoji
            vote_results = {}
            for vote in votes:
                if vote.emoji not in vote_results:
                    vote_results[vote.emoji] = []
                vote_results[vote.emoji].append(vote.display_name)
            
            return vote_results
            
        except Exception as e:
            logger.error(f"Failed to get poll votes: {e}")
            return {}
        finally:
            session.close()
    
    def get_enabled_servers(self) -> List[str]:
        """Get list of guild IDs with enabled polls"""
        session = self.Session()
        try:
            servers = session.query(ServerConfig).filter_by(enabled=True).all()
            return [server.guild_id for server in servers]
        except Exception as e:
            logger.error(f"Failed to get enabled servers: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old polls and votes"""
        session = self.Session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old polls (and their votes will cascade)
            old_polls = session.query(Poll).filter(
                Poll.created_at < cutoff_date
            ).all()
            
            count = len(old_polls)
            for poll in old_polls:
                session.delete(poll)
            
            session.commit()
            logger.info(f"Cleaned up {count} old polls and their votes")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup old data: {e}")
        finally:
            session.close()