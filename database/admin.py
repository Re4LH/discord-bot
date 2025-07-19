#!/usr/bin/env python3
"""
Database administration script for Discord Poll Bot
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from database.models import get_session, ServerConfig, Poll, Vote

def main():
    """Main function for database administration"""
    parser = argparse.ArgumentParser(description='Discord Poll Bot Database Administration')
    parser.add_argument('command', choices=['status', 'migrate', 'cleanup', 'reset'], 
                       help='Command to execute')
    parser.add_argument('--days', type=int, default=30, 
                       help='Days to keep for cleanup (default: 30)')
    parser.add_argument('--force', action='store_true',
                       help='Force reset without confirmation')
    
    args = parser.parse_args()
    
    try:
        db_manager = DatabaseManager()
        
        if args.command == 'status':
            show_database_status(db_manager)
        elif args.command == 'migrate':
            print("Migrating from JSON to database...")
            db_manager.migrate_from_json()
            print("Migration completed!")
        elif args.command == 'cleanup':
            print(f"Cleaning up data older than {args.days} days...")
            db_manager.cleanup_old_data(args.days)
            print("Cleanup completed!")
        elif args.command == 'reset':
            if not args.force:
                confirm = input("This will DELETE ALL data in the database. Are you sure? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Reset cancelled.")
                    return
            reset_database()
            print("Database reset completed!")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def show_database_status(db_manager):
    """Show database status and statistics"""
    session = get_session()
    
    try:
        # Server count
        server_count = session.query(ServerConfig).count()
        enabled_servers = session.query(ServerConfig).filter_by(enabled=True).count()
        
        # Poll count
        total_polls = session.query(Poll).count()
        test_polls = session.query(Poll).filter_by(is_test=True).count()
        real_polls = total_polls - test_polls
        
        # Vote count
        total_votes = session.query(Vote).count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_polls = session.query(Poll).filter(Poll.created_at >= week_ago).count()
        recent_votes = session.query(Vote).filter(Vote.voted_at >= week_ago).count()
        
        print("\n=== Discord Poll Bot Database Status ===")
        print(f"Servers configured: {server_count}")
        print(f"Servers with polls enabled: {enabled_servers}")
        print(f"Total polls created: {total_polls}")
        print(f"  - Real polls: {real_polls}")
        print(f"  - Test polls: {test_polls}")
        print(f"Total votes cast: {total_votes}")
        print(f"Activity (last 7 days):")
        print(f"  - Polls created: {recent_polls}")
        print(f"  - Votes cast: {recent_votes}")
        
        # Show server details
        servers = session.query(ServerConfig).all()
        if servers:
            print("\n=== Server Details ===")
            for server in servers:
                poll_count = session.query(Poll).filter_by(guild_id=server.guild_id).count()
                vote_count = session.query(Vote).join(Poll).filter(Poll.guild_id == server.guild_id).count()
                
                status = "✅ Enabled" if server.enabled else "❌ Disabled"
                print(f"Guild {server.guild_id}: {status}")
                print(f"  Channel: {server.channel_id or 'Not set'}")
                print(f"  Schedule: {server.poll_hour:02d}:{server.poll_minute:02d} {server.timezone}")
                print(f"  Polls: {poll_count}, Votes: {vote_count}")
                print()
                
    finally:
        session.close()

def reset_database():
    """Reset the entire database (delete all data)"""
    from database.models import Base, create_database_engine
    
    engine = create_database_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
if __name__ == '__main__':
    main()