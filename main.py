#!/usr/bin/env python3
"""
Discord Availability Poll Bot
A bot that automatically posts daily availability polls at 8:00 PM
"""

import os
import logging
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands

from bot.scheduler import PollScheduler
from bot.commands import setup_commands
from bot.config import ConfigManager
from database.database_manager import DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AvailabilityBot(commands.Bot):
    """Discord bot for posting daily availability polls"""
    
    def __init__(self):
        # Set up bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_reactions = True
        
        super().__init__(
            command_prefix='!poll ',
            intents=intents,
            help_command=None
        )
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.database_manager = DatabaseManager()
        self.scheduler = PollScheduler(self)
        
        # Migrate from JSON to database if needed
        self.database_manager.migrate_from_json()
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up bot...")
        
        # Set up commands
        await setup_commands(self)
        
        # Start the scheduler
        await self.scheduler.start()
        
        logger.info("Bot setup complete!")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for !poll help"
        )
        await self.change_presence(activity=activity)
        
        # Register the manually posted poll for tracking
        if not hasattr(self, 'active_polls'):
            self.active_polls = {}
            
        # Bot ready with database integration complete
    
    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Initialize config for new guild
        self.config_manager.initialize_guild(guild.id)
        
        # Send welcome message to the first text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    embed = discord.Embed(
                        title="👋 Thanks for adding me!",
                        description="I'm here to help manage daily availability polls for your gaming sessions!",
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="Getting Started",
                        value="Use `!poll setup` to configure your daily polls.",
                        inline=False
                    )
                    embed.add_field(
                        name="Commands",
                        value="Use `!poll help` to see all available commands.",
                        inline=False
                    )
                    await channel.send(embed=embed)
                    break
                except discord.Forbidden:
                    # Try simple text message as fallback
                    try:
                        welcome_text = """👋 Thanks for adding me!
I'm here to help manage daily availability polls for your gaming sessions!

**Getting Started:** Use `!poll setup` to configure your daily polls.
**Commands:** Use `!poll help` to see all available commands."""
                        await channel.send(welcome_text)
                        break
                    except discord.Forbidden:
                        continue
    
    async def on_guild_remove(self, guild):
        """Called when the bot is removed from a guild"""
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")
        
        # Clean up guild configuration
        self.config_manager.remove_guild(guild.id)
    
    async def on_reaction_add(self, reaction, user):
        """Called when someone adds a reaction"""
        # Ignore bot reactions
        if user.bot:
            return
            
        # Check if this is a poll message
        if not hasattr(self, 'active_polls'):
            self.active_polls = {}
            
        message_id = reaction.message.id
        if message_id in self.active_polls:
            # Remove vote from database
            self.database_manager.remove_vote(str(message_id), str(user.id))
            await self.update_poll_results(reaction.message, self.active_polls[message_id])
    
    async def on_reaction_remove(self, reaction, user):
        """Called when someone removes a reaction"""
        # Ignore bot reactions
        if user.bot:
            return
            
        # Check if this is a poll message
        if not hasattr(self, 'active_polls'):
            return
            
        message_id = reaction.message.id
        if message_id in self.active_polls:
            # Remove vote from database
            self.database_manager.remove_vote(str(message_id), str(user.id))
            await self.update_poll_results(reaction.message, self.active_polls[message_id])
    
    async def update_poll_results(self, poll_message, poll_info):
        """Update the poll message with vote results"""
        try:
            # Get votes from database
            vote_results = self.database_manager.get_poll_votes(str(poll_message.id))
            
            # Also check Discord reactions to sync any missing data
            for i, emoji in enumerate(poll_info['emojis']):
                # Find the reaction on the message
                for reaction in poll_message.reactions:
                    if str(reaction.emoji) == emoji:
                        # Get users who reacted (excluding the bot)
                        async for user in reaction.users():
                            if not user.bot:
                                display_name = user.display_name if hasattr(user, 'display_name') else user.name
                                # Save/update vote in database
                                self.database_manager.save_vote(
                                    str(poll_message.id),
                                    str(user.id),
                                    user.name,
                                    display_name,
                                    emoji
                                )
                        break
            
            # Get updated vote results from database
            vote_results = self.database_manager.get_poll_votes(str(poll_message.id))
            
            # Recreate the poll embed with updated results
            poll_date = poll_info.get('poll_date', 'Tomorrow')
            is_test = poll_info.get('is_test', False)
            
            if is_test:
                embed = discord.Embed(
                    title="🧪 Тестова анкета",
                    description=f"<@&1374641326640857088> **Това е тестова анкета - Кой може да играе {poll_date}?**",
                    color=0xffff00,
                    timestamp=datetime.utcnow()
                )
                footer_text = "Това е тестова анкета • Резултатите се обновяват на живо"
            else:
                embed = discord.Embed(
                    title="🎮 Ежедневна анкета за наличност",
                    description=f"<@&1374641326640857088> **Кой може да играе {poll_date}?**",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )
                footer_text = f"Анкета за {poll_message.guild.name} • Резултатите се обновяват на живо"
            
            # Add poll options with votes shown directly under each option
            options_text = ""
            total_voters = set()
            for i, option in enumerate(poll_info['poll_options']):
                emoji = poll_info['emojis'][i]
                voters = vote_results.get(emoji, [])
                
                # Add the option
                options_text += f"{emoji} {option}"
                
                # Add voters if any
                if voters:
                    voter_names = ", ".join(voters)
                    options_text += f"\n    → {voter_names}"
                    total_voters.update(voters)
                
                options_text += "\n"
            
            embed.add_field(
                name="Реагирайте с вашата наличност:",
                value=options_text,
                inline=False
            )
            
            embed.set_footer(text=footer_text)
            
            # Update the poll message
            await poll_message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to update poll results: {e}")
    
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        # Check if the error is due to missing bot permissions
        if isinstance(error, discord.Forbidden):
            logger.error(f"Bot missing permissions in channel {ctx.channel.name} (ID: {ctx.channel.id})")
            try:
                # Try to send a simple message instead of embed
                await ctx.send("❌ I don't have permission to send messages here. Please give me 'Send Messages' and 'Add Reactions' permissions.")
            except:
                # If we can't even send a simple message, log it and continue
                logger.error(f"Cannot send any messages in channel {ctx.channel.name}")
            return
        
        try:
            if isinstance(error, commands.CommandNotFound):
                embed = discord.Embed(
                    title="❌ Command Not Found",
                    description="Unknown command. Use `!poll help` to see available commands.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            elif isinstance(error, commands.MissingPermissions):
                embed = discord.Embed(
                    title="❌ Missing Permissions",
                    description="You don't have permission to use this command.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            elif isinstance(error, commands.BadArgument):
                embed = discord.Embed(
                    title="❌ Invalid Arguments",
                    description=str(error),
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            else:
                logger.error(f"Unhandled command error: {error}")
                embed = discord.Embed(
                    title="❌ An Error Occurred",
                    description="Something went wrong. Please try again later.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
        except discord.Forbidden:
            logger.error(f"Bot cannot send messages in channel {ctx.channel.name} - missing permissions")

async def main():
    """Main function to run the bot"""
    # Get bot token from environment
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        logger.error("Please set your bot token in the .env file or environment.")
        return
    
    # Create and run bot
    bot = AvailabilityBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token! Please check your DISCORD_BOT_TOKEN.")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        if bot.scheduler:
            await bot.scheduler.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
