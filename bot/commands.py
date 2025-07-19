"""
Command handlers for the Discord bot
"""

import logging
from datetime import datetime
import discord
from discord.ext import commands
import pytz

logger = logging.getLogger(__name__)

async def setup_commands(bot):
    """Set up all bot commands"""
    
    @bot.command(name='help')
    async def help_command(ctx):
        """Show help information"""
        try:
            embed = discord.Embed(
                title="🤖 Бот за анкети за наличност - Помощ",
                description="Помагам за управление на ежедневни анкети за наличност за игрални сесии!",
                color=0x0099ff
            )
            
            # Admin commands
            if ctx.author.guild_permissions.manage_guild:
                embed.add_field(
                    name="📋 Админ команди",
                    value="""
                    `!poll setup` - Настройване на ежедневни анкети за този сървър
                    `!poll channel <#канал>` - Задаване на канал за анкети
                    `!poll time <час> [минута]` - Задаване на време за анкета (24ч формат)
                    `!poll timezone <часова зона>` - Задаване на часова зона
                    `!poll options` - Конфигуриране на опции за анкета
                    `!poll enable` - Включване на ежедневни анкети
                    `!poll disable` - Изключване на ежедневни анкети
                    `!poll test` - Публикуване на тестова анкета
                    """,
                    inline=False
                )
            
            # General commands
            embed.add_field(
                name="ℹ️ Общи команди",
                value="""
                `!poll status` - Показване на текущата конфигурация
                `!poll next` - Показване на времето за следващата анкета
                `!poll help` - Показване на това съобщение за помощ
                `!poll permissions` - Проверка на разрешенията на бота
                """,
                inline=False
            )
            
            embed.add_field(
                name="⏰ Настройки по подразбиране",
                value="• Време: 8:00 сутрин (08:00)\n• Часова зона: UTC\n• 7 опции за наличност",
                inline=False
            )
            
            embed.set_footer(text="Use !poll <command> to run commands")
            
            await ctx.send(embed=embed)
        except discord.Forbidden:
            # Fallback to simple text if embeds don't work
            help_text = """**🤖 Availability Poll Bot - Help**
I help manage daily availability polls for gaming sessions!

**📋 Admin Commands** (if you have Manage Server permission):
• `!poll setup` - Set up daily polls for this server
• `!poll channel #channel` - Set poll channel
• `!poll time <hour> [minute]` - Set poll time (24h format)
• `!poll timezone <timezone>` - Set timezone
• `!poll enable` - Enable daily polls
• `!poll disable` - Disable daily polls
• `!poll test` - Post a test poll

**ℹ️ General Commands:**
• `!poll status` - Show current configuration
• `!poll next` - Show next scheduled poll time
• `!poll help` - Show this help message
• `!poll permissions` - Check bot permissions

**⏰ Default Settings:**
• Time: 8:00 PM (20:00)
• Timezone: UTC
• 6 availability options

Use `!poll <command>` to run commands"""
            await ctx.send(help_text)
    
    @bot.command(name='setup')
    async def setup_command(ctx):
        """Interactive setup for the bot"""
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.manage_guild and not ctx.author.guild_permissions.administrator:
            try:
                await ctx.send("❌ You need 'Manage Server' or 'Administrator' permission to set up the bot.")
                return
            except discord.Forbidden:
                logger.error(f"Cannot send permission error message in {ctx.channel.name}")
                return
        
        try:
            embed = discord.Embed(
                title="🛠️ Server Setup",
                description="Let's configure daily availability polls for your server!",
                color=0x00ff00
            )
            
            # Initialize guild config if not exists
            guild_id = str(ctx.guild.id)
            bot.config_manager.initialize_guild(guild_id)
            
            embed.add_field(
                name="Step 1: Set Channel",
                value=f"Use `!poll channel #{ctx.channel.name}` to set this as the poll channel",
                inline=False
            )
            
            embed.add_field(
                name="Step 2: Set Time (Optional)",
                value="Use `!poll time 20 0` to set poll time (default: 8:00 PM)",
                inline=False
            )
            
            embed.add_field(
                name="Step 3: Set Timezone (Optional)",
                value="Use `!poll timezone America/New_York` (default: UTC)",
                inline=False
            )
            
            embed.add_field(
                name="Step 4: Enable Polls",
                value="Use `!poll enable` to start daily polls",
                inline=False
            )
            
            embed.set_footer(text="You can customize poll options later with !poll options")
            
            await ctx.send(embed=embed)
        except discord.Forbidden:
            # Fallback to simple text
            setup_text = f"""**🛠️ Server Setup**
Let's configure daily availability polls for your server!

**Step 1: Set Channel**
Use `!poll channel #{ctx.channel.name}` to set this as the poll channel

**Step 2: Set Time (Optional)**
Use `!poll time 20 0` to set poll time (default: 8:00 PM)

**Step 3: Set Timezone (Optional)**
Use `!poll timezone America/New_York` (default: UTC)

**Step 4: Enable Polls**
Use `!poll enable` to start daily polls

You can customize poll options later with `!poll options`"""
            await ctx.send(setup_text)
    
    @bot.command(name='channel')
    async def channel_command(ctx, channel: discord.TextChannel = None):
        """Set the channel for daily polls"""
        if not channel:
            channel = ctx.channel
        
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        # Check bot permissions in the target channel
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.send_messages or not permissions.add_reactions:
            embed = discord.Embed(
                title="❌ Insufficient Permissions",
                description=f"I need 'Send Messages' and 'Add Reactions' permissions in {channel.mention}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        # Update config
        config['channel_id'] = str(channel.id)
        bot.config_manager.save_guild_config(guild_id, config)
        
        embed = discord.Embed(
            title="✅ Channel Set",
            description=f"Daily polls will be posted in {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @bot.command(name='time')
    async def time_command(ctx, hour: int, minute: int = 0):
        """Set the time for daily polls (24-hour format)"""
        if not (0 <= hour <= 23):
            embed = discord.Embed(
                title="❌ Invalid Hour",
                description="Hour must be between 0 and 23 (24-hour format)",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if not (0 <= minute <= 59):
            embed = discord.Embed(
                title="❌ Invalid Minute",
                description="Minute must be between 0 and 59",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        config['poll_hour'] = hour
        config['poll_minute'] = minute
        bot.config_manager.save_guild_config(guild_id, config)
        
        # Reschedule if polls are enabled
        if config.get('enabled', False):
            await bot.scheduler.schedule_guild_poll(guild_id, config)
        
        embed = discord.Embed(
            title="✅ Time Updated",
            description=f"Daily polls will be posted at {hour:02d}:{minute:02d}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @bot.command(name='timezone')
    @commands.has_permissions(manage_guild=True)
    async def timezone_command(ctx, timezone_name: str):
        """Set the timezone for daily polls"""
        try:
            # Validate timezone
            pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError:
            embed = discord.Embed(
                title="❌ Invalid Timezone",
                description=f"Unknown timezone: {timezone_name}\nExample: `America/New_York`, `Europe/London`, `Asia/Tokyo`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        config['timezone'] = timezone_name
        bot.config_manager.save_guild_config(guild_id, config)
        
        # Reschedule if polls are enabled
        if config.get('enabled', False):
            await bot.scheduler.schedule_guild_poll(guild_id, config)
        
        embed = discord.Embed(
            title="✅ Timezone Updated",
            description=f"Timezone set to: {timezone_name}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @bot.command(name='enable')
    async def enable_command(ctx):
        """Enable daily polls"""
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        # Check if channel is set
        if not config.get('channel_id'):
            embed = discord.Embed(
                title="❌ No Channel Set",
                description="Please set a channel first using `!poll channel #channel-name`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        config['enabled'] = True
        bot.config_manager.save_guild_config(guild_id, config)
        
        # Schedule the daily poll
        await bot.scheduler.schedule_guild_poll(guild_id, config)
        
        embed = discord.Embed(
            title="✅ Polls Enabled",
            description="Daily availability polls are now enabled!",
            color=0x00ff00
        )
        
        # Show next poll time
        next_time = bot.scheduler.get_next_poll_time(guild_id)
        if next_time:
            embed.add_field(
                name="Next Poll",
                value=f"<t:{int(next_time.timestamp())}:F>",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @bot.command(name='disable')
    @commands.has_permissions(manage_guild=True)
    async def disable_command(ctx):
        """Disable daily polls"""
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        config['enabled'] = False
        bot.config_manager.save_guild_config(guild_id, config)
        
        # Unschedule the daily poll
        await bot.scheduler.unschedule_guild_poll(guild_id)
        
        embed = discord.Embed(
            title="✅ Polls Disabled",
            description="Daily availability polls have been disabled.",
            color=0xffff00
        )
        await ctx.send(embed=embed)
    
    @bot.command(name='test')
    async def test_command(ctx):
        """Post a test poll"""
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        try:
            await bot.scheduler.post_test_poll(ctx.channel, config)
            embed = discord.Embed(
                title="✅ Test Poll Posted",
                description="Check the test poll above!",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Post Test Poll",
                description=f"Error: {str(e)}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @bot.command(name='status')
    async def status_command(ctx):
        """Show current configuration"""
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        embed = discord.Embed(
            title="📊 Server Configuration",
            color=0x0099ff
        )
        
        # Basic info
        enabled = config.get('enabled', False)
        embed.add_field(
            name="Status",
            value="✅ Enabled" if enabled else "❌ Disabled",
            inline=True
        )
        
        # Channel
        channel_id = config.get('channel_id')
        if channel_id:
            channel = ctx.guild.get_channel(int(channel_id))
            channel_name = channel.mention if channel else "❌ Channel not found"
        else:
            channel_name = "❌ Not set"
        
        embed.add_field(
            name="Channel",
            value=channel_name,
            inline=True
        )
        
        # Time
        hour = config.get('poll_hour', 20)
        minute = config.get('poll_minute', 0)
        embed.add_field(
            name="Time",
            value=f"{hour:02d}:{minute:02d}",
            inline=True
        )
        
        # Timezone
        timezone = config.get('timezone', 'UTC')
        embed.add_field(
            name="Timezone",
            value=timezone,
            inline=True
        )
        
        # Next poll time
        if enabled:
            next_time = bot.scheduler.get_next_poll_time(guild_id)
            if next_time:
                embed.add_field(
                    name="Next Poll",
                    value=f"<t:{int(next_time.timestamp())}:R>",
                    inline=True
                )
        
        await ctx.send(embed=embed)
    
    @bot.command(name='next')
    async def next_command(ctx):
        """Show next scheduled poll time"""
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        if not config.get('enabled', False):
            embed = discord.Embed(
                title="❌ Polls Disabled",
                description="Daily polls are currently disabled. Use `!poll enable` to enable them.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        next_time = bot.scheduler.get_next_poll_time(guild_id)
        
        if next_time:
            embed = discord.Embed(
                title="⏰ Next Poll",
                description=f"The next poll will be posted <t:{int(next_time.timestamp())}:R>",
                color=0x00ff00
            )
            embed.add_field(
                name="Exact Time",
                value=f"<t:{int(next_time.timestamp())}:F>",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ No Poll Scheduled",
                description="No poll is currently scheduled.",
                color=0xff0000
            )
        
        await ctx.send(embed=embed)
    
    @bot.command(name='options')
    @commands.has_permissions(manage_guild=True)
    async def options_command(ctx):
        """Show current poll options"""
        guild_id = str(ctx.guild.id)
        config = bot.config_manager.get_guild_config(guild_id)
        
        poll_options = config.get('poll_options', bot.scheduler.default_poll_options)
        
        embed = discord.Embed(
            title="📝 Current Poll Options",
            description="These are the current availability options for polls:",
            color=0x0099ff
        )
        
        options_text = ""
        for i, option in enumerate(poll_options[:6]):
            emoji = bot.scheduler.poll_emojis[i]
            options_text += f"{emoji} {option}\n"
        
        embed.add_field(
            name="Options",
            value=options_text,
            inline=False
        )
        
        embed.add_field(
            name="Note",
            value="Currently using default options. Custom option editing will be added in a future update!",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @bot.command(name='permissions')
    async def permissions_command(ctx):
        """Check bot permissions in this channel"""
        permissions = ctx.channel.permissions_for(ctx.guild.me)
        
        # List of permissions we need
        needed_perms = {
            'send_messages': 'Send Messages',
            'add_reactions': 'Add Reactions', 
            'embed_links': 'Embed Links',
            'use_external_emojis': 'Use External Emojis'
        }
        
        response = f"**Bot Permissions in #{ctx.channel.name}:**\n\n"
        
        for perm, display_name in needed_perms.items():
            has_perm = getattr(permissions, perm, False)
            status = "✅" if has_perm else "❌"
            response += f"{status} {display_name}\n"
        
        response += f"\n**Bot can function:** {'✅ Yes' if all(getattr(permissions, p) for p in needed_perms) else '❌ No'}"
        
        try:
            await ctx.send(response)
        except discord.Forbidden:
            # If we can't send the message, try to log it at least
            logger.error(f"Cannot send permissions check in {ctx.channel.name} - missing send_messages permission")
    
    @bot.command(name='findchannel')
    async def find_channel_command(ctx):
        """Find channels where the bot can send messages"""
        working_channels = []
        
        for channel in ctx.guild.text_channels:
            perms = channel.permissions_for(ctx.guild.me)
            if perms.send_messages and perms.add_reactions:
                working_channels.append(f"#{channel.name}")
        
        if working_channels:
            response = f"**Channels where I can work:**\n" + "\n".join(working_channels)
            response += f"\n\nTry using commands in one of these channels!"
        else:
            response = "❌ I don't have permissions in any channels. Please give me 'Send Messages' and 'Add Reactions' permissions."
        
        # Try to send to current channel first, then try other channels
        try:
            await ctx.send(response)
        except discord.Forbidden:
            # Try to send to the first working channel
            for channel in ctx.guild.text_channels:
                perms = channel.permissions_for(ctx.guild.me)
                if perms.send_messages:
                    try:
                        await channel.send(f"**Bot Status Report:**\n{response}")
                        break
                    except discord.Forbidden:
                        continue
    
    @bot.command(name='checkme')
    async def check_user_permissions(ctx):
        """Check what permissions the user has"""
        user_perms = ctx.author.guild_permissions
        
        response = f"**Your permissions in this server:**\n\n"
        
        # Check important permissions for bot setup
        important_perms = {
            'administrator': 'Administrator (can do everything)',
            'manage_guild': 'Manage Server (can set up bot)',
            'manage_channels': 'Manage Channels',
            'manage_roles': 'Manage Roles'
        }
        
        for perm, description in important_perms.items():
            has_perm = getattr(user_perms, perm, False)
            status = "✅" if has_perm else "❌"
            response += f"{status} {description}\n"
        
        if user_perms.administrator or user_perms.manage_guild:
            response += f"\n✅ **You can set up the bot!** Use `!poll setup` to start."
        else:
            response += f"\n❌ **You need 'Manage Server' or 'Administrator' permission to set up the bot.**"
            response += f"\nAsk a server admin to either:"
            response += f"\n1. Give you the 'Manage Server' permission"
            response += f"\n2. Set up the bot themselves using `!poll setup`"
        
        await ctx.send(response)
    
    @bot.command(name='manual')
    @commands.has_permissions(manage_guild=True)
    async def manual_poll_command(ctx, action=None):
        """Manually trigger polls - !manual now or !manual daily"""
        if action is None:
            embed = discord.Embed(
                title="📊 Ръчни команди за анкети",
                description="Налични команди за анкети:",
                color=0x0099ff
            )
            embed.add_field(
                name="!manual now",
                value="Публикува анкета незабавно в текущия канал",
                inline=False
            )
            embed.add_field(
                name="!manual daily", 
                value="Публикува истинска ежедневна анкета (същата като автоматичната в 5:00 ч)",
                inline=False
            )
            await ctx.send(embed=embed)
            return
            
        if action.lower() == 'now':
            # Post poll in current channel immediately
            config = bot.config_manager.get_guild_config(str(ctx.guild.id))
            try:
                message = await bot.scheduler.post_test_poll(ctx.channel, config)
                await ctx.send("✅ Анкетата е публикувана! Резултатите се обновяват на живо.")
            except Exception as e:
                await ctx.send(f"❌ Грешка при публикуване на анкетата: {e}")
                
        elif action.lower() == 'daily':
            # Post real daily poll in configured channel
            try:
                await bot.scheduler.post_daily_poll(str(ctx.guild.id))
                await ctx.send("✅ Ежедневната анкета е публикувана в конфигурирания канал!")
            except Exception as e:
                await ctx.send(f"❌ Грешка при публикуване на ежедневната анкета: {e}")
        else:
            await ctx.send("❌ Невалидна команда. Използвайте `!manual now` или `!manual daily`")
    
    # Error handlers for specific commands
    @setup_command.error
    @channel_command.error
    @time_command.error
    @timezone_command.error
    @enable_command.error
    @disable_command.error
    @test_command.error
    @options_command.error
    @manual_poll_command.error
    async def admin_command_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="You need 'Manage Server' permission to use admin commands.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    logger.info("Commands set up successfully")
