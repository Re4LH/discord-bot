"""
Scheduler module for managing daily poll posting
"""

import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, List
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

logger = logging.getLogger(__name__)

class PollScheduler:
    """Manages scheduling and posting of daily availability polls"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = bot.config_manager
        self.scheduler = AsyncIOScheduler(timezone=pytz.UTC)
        
        # Default poll options with emojis
        self.default_poll_options = [
            "✅ Available all day",
            "🌅 Available morning (9 AM - 12 PM)",
            "☀️ Available afternoon (12 PM - 6 PM)",
            "🌙 Available evening (6 PM - 11 PM)",
            "🌃 Available late night (11 PM+)",
            "🤔 Not sure",
            "❌ Not available"
        ]
        
        # Emoji reactions for voting
        self.poll_emojis = ["✅", "🌅", "☀️", "🌙", "🌃", "🤔", "❌"]
    
    async def start(self):
        """Start the scheduler"""
        logger.info("Starting poll scheduler...")
        
        # Schedule daily polls for all configured guilds
        await self.schedule_all_guilds()
        
        # Start the scheduler
        self.scheduler.start()
        logger.info("Poll scheduler started successfully")
    
    async def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Poll scheduler stopped")
    
    async def schedule_all_guilds(self):
        """Schedule daily polls for all configured guilds"""
        configs = self.bot.config_manager.get_all_configs()
        
        for guild_id, config in configs.items():
            if config.get('enabled', False):
                await self.schedule_guild_poll(guild_id, config)
    
    async def schedule_guild_poll(self, guild_id: str, config: dict):
        """Schedule daily poll for a specific guild"""
        try:
            # Get timezone (default to UTC)
            timezone_str = config.get('timezone', 'UTC')
            timezone = pytz.timezone(timezone_str)
            
            # Get poll time (default to 20:00)
            poll_hour = config.get('poll_hour', 20)
            poll_minute = config.get('poll_minute', 0)
            
            # Create cron trigger for daily execution
            trigger = CronTrigger(
                hour=poll_hour,
                minute=poll_minute,
                timezone=timezone
            )
            
            # Schedule the job
            job_id = f"daily_poll_{guild_id}"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Add new job
            self.scheduler.add_job(
                self.post_daily_poll,
                trigger=trigger,
                args=[guild_id],
                id=job_id,
                name=f"Daily Poll for Guild {guild_id}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled daily poll for guild {guild_id} at {poll_hour:02d}:{poll_minute:02d} {timezone_str}")
            
        except Exception as e:
            logger.error(f"Failed to schedule poll for guild {guild_id}: {e}")
    
    async def unschedule_guild_poll(self, guild_id: str):
        """Remove scheduled poll for a specific guild"""
        job_id = f"daily_poll_{guild_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled daily poll for guild {guild_id}")
    
    async def post_daily_poll(self, guild_id: str):
        """Post the daily availability poll"""
        try:
            # Get guild and config
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return
            
            config = self.bot.config_manager.get_guild_config(guild_id)
            if not config or not config.get('enabled', False):
                logger.info(f"Polls disabled for guild {guild_id}")
                return
            
            # Get channel
            channel_id = config.get('channel_id')
            if not channel_id:
                logger.error(f"No channel configured for guild {guild_id}")
                return
            
            channel = guild.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel {channel_id} not found in guild {guild_id}")
                return
            
            # Calculate tomorrow's date in Bulgarian timezone
            bulgaria_tz = pytz.timezone('Europe/Sofia')
            today = datetime.now(bulgaria_tz)
            tomorrow = today + timedelta(days=1)
            
            # Bulgarian day names
            bulgarian_days = {
                'Monday': 'понedelник',
                'Tuesday': 'вторник', 
                'Wednesday': 'сряда',
                'Thursday': 'четвъртък',
                'Friday': 'петък',
                'Saturday': 'съботa',
                'Sunday': 'неделя'
            }
            
            # Bulgarian month names
            bulgarian_months = {
                'January': 'януари', 'February': 'февруари', 'March': 'март',
                'April': 'април', 'May': 'май', 'June': 'юни',
                'July': 'юли', 'August': 'август', 'September': 'септември',
                'October': 'октомври', 'November': 'ноември', 'December': 'декември'
            }
            
            # Format date in Bulgarian
            day_name = bulgarian_days[tomorrow.strftime('%A')]
            month_name = bulgarian_months[tomorrow.strftime('%B')]
            formatted_date = f"{day_name}, {tomorrow.day} {month_name} {tomorrow.year}"
            
            # Create poll embed with vote tracking
            embed = discord.Embed(
                title="🎮 Ежедневна анкета за наличност",
                description=f"<@&1374641326640857088> **Кой може да играе утре {formatted_date}?**",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            # Add poll options
            poll_options = config.get('poll_options', self.default_poll_options)
            options_text = ""
            for i, option in enumerate(poll_options[:7]):  # Updated to 7 options
                emoji = self.poll_emojis[i]
                options_text += f"{emoji} {option}\n"
            
            embed.add_field(
                name="Реагирайте с вашата наличност:",
                value=options_text,
                inline=False
            )
            
            # Add footer
            embed.set_footer(text=f"Анкета за {guild.name} • Резултатите се обновяват на живо")
            
            # Clean up old polls (keep only last 2)
            poll_history = config.get('poll_history', [])
            if len(poll_history) >= 2:
                # Delete the oldest poll
                oldest_poll_id = poll_history[0]
                try:
                    oldest_message = await channel.fetch_message(oldest_poll_id)
                    await oldest_message.delete()
                    logger.info(f"Deleted old poll message {oldest_poll_id}")
                except discord.NotFound:
                    logger.info(f"Old poll message {oldest_poll_id} already deleted")
                except discord.HTTPException as e:
                    logger.warning(f"Failed to delete old poll {oldest_poll_id}: {e}")
                
                # Remove from history
                poll_history.pop(0)
            
            # Send the poll
            message = await channel.send(embed=embed)
            
            # Add reactions
            for i, _ in enumerate(poll_options[:7]):
                try:
                    await message.add_reaction(self.poll_emojis[i])
                except discord.HTTPException:
                    logger.warning(f"Failed to add reaction {self.poll_emojis[i]}")
            
            # Store poll info for reaction tracking
            poll_info = {
                'poll_message_id': message.id,
                'vote_message_id': message.id,  # Same message now
                'channel_id': channel.id,
                'guild_id': guild_id,
                'poll_options': poll_options[:7],
                'emojis': self.poll_emojis[:7],
                'poll_date': f"утре {formatted_date}"
            }
            
            # Add new poll to history
            poll_history.append(message.id)
            config['poll_history'] = poll_history
            
            # Save updated config
            self.config_manager.configs[guild_id] = config
            self.config_manager.save_configs()
            
            # Create poll record in database
            poll_db_id = self.bot.database_manager.create_poll(
                guild_id, channel.id, message.id, formatted_date, is_test=False
            )
            
            # Store poll info for reaction tracking
            if not hasattr(self.bot, 'active_polls'):
                self.bot.active_polls = {}
            self.bot.active_polls[message.id] = poll_info
            
            logger.info(f"Posted daily poll in guild {guild_id}, channel {channel_id}")
            logger.info(f"Created poll record with ID {poll_db_id} in database")
            
        except discord.Forbidden:
            logger.error(f"No permission to send messages in guild {guild_id}")
        except Exception as e:
            logger.error(f"Failed to post daily poll for guild {guild_id}: {e}")
    
    async def post_test_poll(self, channel, config: dict):
        """Post a test poll immediately"""
        try:
            # Get tomorrow's date for test in Bulgarian timezone
            bulgaria_tz = pytz.timezone('Europe/Sofia')
            today = datetime.now(bulgaria_tz)
            tomorrow = today + timedelta(days=1)
            
            # Bulgarian day names
            bulgarian_days = {
                'Monday': 'понedelник',
                'Tuesday': 'вторник', 
                'Wednesday': 'сряда',
                'Thursday': 'четвъртък',
                'Friday': 'петък',
                'Saturday': 'съботa',
                'Sunday': 'неделя'
            }
            
            # Bulgarian month names
            bulgarian_months = {
                'January': 'януари', 'February': 'февруари', 'March': 'март',
                'April': 'април', 'May': 'май', 'June': 'юни',
                'July': 'юли', 'August': 'август', 'September': 'септември',
                'October': 'октомври', 'November': 'ноември', 'December': 'декември'
            }
            
            # Format date in Bulgarian
            day_name = bulgarian_days[tomorrow.strftime('%A')]
            month_name = bulgarian_months[tomorrow.strftime('%B')]
            formatted_date = f"{day_name}, {tomorrow.day} {month_name} {tomorrow.year}"
            
            # Create test poll embed
            embed = discord.Embed(
                title="🧪 Тестова анкета",
                description=f"<@&1374641326640857088> **Това е тестова анкета - Кой може да играе утре {formatted_date}?**",
                color=0xffff00,
                timestamp=datetime.utcnow()
            )
            
            # Add poll options
            poll_options = config.get('poll_options', self.default_poll_options)
            options_text = ""
            for i, option in enumerate(poll_options[:7]):
                emoji = self.poll_emojis[i]
                options_text += f"{emoji} {option}\n"
            
            embed.add_field(
                name="Реагирайте с вашата наличност:",
                value=options_text,
                inline=False
            )
            
            embed.set_footer(text="Това е тестова анкета • Резултатите се обновяват на живо")
            
            # Send the poll
            message = await channel.send(embed=embed)
            
            # Add reactions
            for i, _ in enumerate(poll_options[:7]):
                try:
                    await message.add_reaction(self.poll_emojis[i])
                except discord.HTTPException:
                    logger.warning(f"Failed to add reaction {self.poll_emojis[i]}")
            
            # Store poll info for reaction tracking
            poll_info = {
                'poll_message_id': message.id,
                'vote_message_id': message.id,  # Same message now
                'channel_id': channel.id,
                'guild_id': str(channel.guild.id),
                'poll_options': poll_options[:7],
                'emojis': self.poll_emojis[:7],
                'is_test': True,
                'poll_date': f"утре {formatted_date}"
            }
            
            # Create poll record in database
            poll_db_id = self.bot.database_manager.create_poll(
                str(channel.guild.id), channel.id, message.id, formatted_date, is_test=True
            )
            
            # Store poll info for reaction tracking
            if not hasattr(self.bot, 'active_polls'):
                self.bot.active_polls = {}
            self.bot.active_polls[message.id] = poll_info
            
            logger.info(f"Created test poll record with ID {poll_db_id} in database")
            return message
            
        except Exception as e:
            logger.error(f"Failed to post test poll: {e}")
            raise
    
    def get_next_poll_time(self, guild_id: str) -> datetime:
        """Get the next scheduled poll time for a guild"""
        job_id = f"daily_poll_{guild_id}"
        job = self.scheduler.get_job(job_id)
        
        if job and job.next_run_time:
            return job.next_run_time
        
        return None
