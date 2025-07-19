# Discord Availability Poll Bot

## Overview

This is a Discord bot designed to automatically post daily availability polls for gaming sessions or group activities. The bot allows server administrators to configure when and where polls are posted, and provides a simple voting system using emoji reactions.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular Python architecture using the discord.py library for Discord integration. The system is designed around a central bot class that coordinates between multiple specialized modules for different functionalities.

### Core Architecture Components:
- **Main Application** (`main.py`): Entry point and bot initialization
- **Command System** (`bot/commands.py`): Discord slash commands and user interactions
- **Configuration Management** (`bot/config.py`): Server-specific settings and persistence
- **Scheduler System** (`bot/scheduler.py`): Automated poll posting using APScheduler
- **JSON Storage** (`config/servers.json`): Simple file-based configuration storage

## Key Components

### Bot Core (`main.py`)
- **Purpose**: Application entry point and Discord bot initialization
- **Key Features**: 
  - Environment variable loading with python-dotenv
  - Logging configuration for both file and console output
  - Discord intents setup for necessary permissions
  - Bot lifecycle management

### Command Handler (`bot/commands.py`)
- **Purpose**: Manages all user-facing Discord commands
- **Key Features**:
  - Administrative commands for bot configuration
  - User commands for checking status and next poll times
  - Permission-based command access (admin vs general users)
  - Embedded Discord messages for rich formatting

### Configuration Manager (`bot/config.py`)
- **Purpose**: Handles server-specific settings and persistence
- **Key Features**:
  - JSON-based configuration storage
  - Default configuration templates
  - Automatic directory creation
  - Error handling for file operations

### Poll Scheduler (`bot/scheduler.py`)
- **Purpose**: Manages automated poll posting using APScheduler
- **Key Features**:
  - Timezone-aware scheduling using pytz
  - Cron-based daily poll posting
  - Customizable poll options with emoji reactions
  - Support for multiple Discord servers with different schedules

## Data Flow

1. **Bot Startup**: Load environment variables → Initialize Discord bot → Load server configurations → Start scheduler
2. **Command Processing**: Receive Discord command → Validate permissions → Execute command logic → Update configuration → Save to JSON
3. **Scheduled Polling**: Scheduler triggers → Load server config → Create poll embed → Post to configured channel → Add emoji reactions
4. **Configuration Updates**: Admin command → Validate input → Update in-memory config → Persist to JSON file

## External Dependencies

### Core Libraries:
- **discord.py**: Discord API integration and bot framework
- **APScheduler**: Asynchronous job scheduling for daily polls
- **pytz**: Timezone handling for accurate scheduling
- **python-dotenv**: Environment variable management

### Data Storage:
- **JSON Files**: Simple file-based storage for server configurations
- **Local File System**: Log files and configuration persistence

### Environment Requirements:
- **DISCORD_TOKEN**: Bot authentication token from Discord Developer Portal

## Deployment Strategy

### Local Development:
- Environment variables loaded from `.env` file
- JSON configuration files stored locally in `config/` directory
- Logging to both console and `bot.log` file

### Production Considerations:
- Bot token should be provided via environment variables
- Configuration files need persistent storage across restarts
- Logging should be configured for production monitoring
- Error handling for network connectivity issues

### Architecture Benefits:
1. **Modularity**: Clear separation of concerns across different modules
2. **Scalability**: JSON-based config allows multiple Discord servers
3. **Maintainability**: Simple file-based storage with clear data structures
4. **Flexibility**: Configurable poll times, channels, and options per server

### Known Limitations:
1. **Single Point of Failure**: Bot must stay online for scheduled polls
2. **File-Based Storage**: No data redundancy or backup strategy
3. **Memory State**: Configuration changes require file I/O operations

## Recent Changes

### July 19, 2025 - Database Integration & Final Implementation
- **NEW**: Integrated PostgreSQL database for persistent data storage
- **NEW**: Migrated from JSON file storage to database with automatic migration
- **NEW**: Database stores server configs, polls, and individual votes with full history
- **NEW**: Added database administration tools for monitoring and maintenance
- Completed Discord availability poll bot with live vote tracking
- Added "Not sure" option to poll choices (7 total options)
- Implemented nicknames displayed directly under poll options
- Changed poll time from 8:00 PM to 5:00 AM UTC per user request
- Added @heartbreakers role tag to poll questions
- Implemented automatic cleanup (keeps only last 3 polls in database)
- Fully translated interface to Bulgarian language
- Fixed Bulgarian date formatting with proper timezone (Europe/Sofia)
- Added manual poll commands: `!manual now` and `!manual daily`
- Fixed configuration save errors in scheduler
- Bot successfully connected and running continuously targeting #announce-sign channel