#!/usr/bin/env python3
import json

import discord
from discord import app_commands
from discord.ext import tasks

from datetime import datetime, timezone, timedelta

import os
from dotenv import load_dotenv

import aiohttp
from bs4 import BeautifulSoup

from util.monitor import (
    send_activity_embed,
    send_serverchange_embed
)
from util.battlemetrics import (
    get_online_server,
    get_battlemetrics_player,
    get_recently_visited_servers

)
from util.correlate import find_overlapping_sessions
from util.search import search_player
from util.steamfind import build_steamfind_embed
from util.streamermode import get_streamermode_name
from util.general import get_steam_avatar

from typing import Optional
import math
import re

# Load environment variables from .env file
load_dotenv()

description = """
A Discord bot to monitor and correlate player data from BattleMetrics.
Combines search and correlation functionality with Discord integration.
"""

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
BASE_URL = "https://api.battlemetrics.com"

monitor_channel_id = os.getenv('MONITOR_CHANNEL_ID')
monitored_users_file = os.getenv('MONITORED_IDS_JSON_FILE')

def load_monitored_ids():
    try:
        with open(monitored_users_file, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_monitored_ids(ids):
    with open(monitored_users_file, 'w') as f:
        json.dump(list(ids), f)


seen_ids = set()  # To track seen player IDs
user_status = {}  # To store status of monitored players
battlemetrics_ids = load_monitored_ids()  # To store IDs of monitored players


def create_embed(title, description, fields=None, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    return embed


class BasePaginationView(discord.ui.View):
    """
    Base class for pagination views to reduce code duplication.
    Handles common pagination functionality.
    """
    def __init__(self, pages: list[discord.Embed], timeout: int = 300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.message = None
        self.update_buttons()
    
    def update_buttons(self):
        if len(self.pages) <= 1:
            for button in self.children:
                button.disabled = True
        else:
            for button in self.children:
                if button.emoji in ["⏪", "◀️"]:
                    button.disabled = self.current_page == 0
                elif button.emoji in ["▶️", "⏩"]:
                    button.disabled = self.current_page == len(self.pages) - 1

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.primary)
    async def rewind(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.primary)
    async def fast_forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    async def on_timeout(self):
        self.clear_items()

class SearchPaginationView(BasePaginationView):
    """Pagination view specifically for search results."""
    pass  # Inherits all functionality from base class

class HistoryPaginationView(BasePaginationView):
    """Pagination view specifically for persona history."""
    pass  # Inherits all functionality from base class

class CorrelationPaginationView(BasePaginationView):
    """
    Pagination view for correlation results with additional functionality.
    """
    def __init__(self, overlapping_sessions: list, player_names: dict, days: int, access_token: bool = False):
        self.items_per_page = 5
        pages = self.create_embed_pages(overlapping_sessions, player_names, days, access_token, self.items_per_page)
        super().__init__(pages)
        

    def create_embed_pages(self, overlapping_sessions, player_names, days, access_token, items_per_page):
        pages = []
        total_sessions = len(overlapping_sessions)
        total_pages = math.ceil(total_sessions / items_per_page)

        for page_num in range(total_pages):
            start_idx = page_num * items_per_page
            end_idx = min(start_idx + items_per_page, total_sessions)
            current_sessions = overlapping_sessions[start_idx:end_idx]

            title = "🎮 BattleMetrics Session Correlation"

            base_description = f"🔍 Found {total_sessions} overlapping sessions in the last {days} days:"
            if access_token:
                base_description = "🔐 Access Token authentication used.\n" + base_description

            embed = discord.Embed(title=title, description=base_description, color=discord.Color.blue())

            for i, session in enumerate(current_sessions, start=start_idx + 1):
                start_timestamp = int(session['start'].timestamp())
                stop_timestamp = int(session['stop'].timestamp())
                
                players = []
                for player in session['players']:
                    players.append(f"{player_names[player]} ({player})")

                session_info = (
                    f"🕒 Start: <t:{start_timestamp}:f> (<t:{start_timestamp}:R>)\n"
                    f"🛑 Stop: <t:{stop_timestamp}:f> (<t:{stop_timestamp}:R>)\n"
                    f"⏱️ Duration: {session['duration']}\n"
                    f"👥 Players: {', '.join(players)}\n"
                    f"🔗 [View Server](https://battlemetrics.com/servers/rust/{session['server_id']})"
                )

                embed.add_field(
                    name=f"Overlap #{i} (🖥️ Server: {session['server_id']})",
                    value=session_info,
                    inline=False
                )
            
            embed.set_footer(text=f"Page {page_num+1} • Entries {start_idx+1}-{end_idx} of {total_sessions} • Made by seall.dev", 
                        icon_url="https://seall.dev/images/logo.png")
            pages.append(embed)
        return pages

@client.event
async def on_ready():
    await tree.sync()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f'[{timestamp}] Bot is ready! Logged in as {client.user.name}')
    monitor_loop.start()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] Monitor loop started!")

@tree.command(name="streamername", description="Finds the Streamer Mode name from a Steam ID")
async def streamername(interaction: discord.Interaction, steam_id: str):
    await interaction.response.defer()

    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed streamername command - steam_id:{steam_id}")
    
    username = get_streamermode_name(steam_id)

    embed = discord.Embed(
        title=f"Streamer Mode Name for `{steam_id}`",
        color=discord.Color.blue(),
        description=f"**Username 👤:** {username}"
    )

    url = get_steam_avatar(steam_id)

    if url:
        embed.set_thumbnail(url=url)

    embed.set_footer(text=f"Made by seall.dev", 
            icon_url="https://seall.dev/images/logo.png")

    await interaction.edit_original_response(embed=embed)

@tree.command(name="steamfind", description="Provide Google dork URLs and Steam search URLs for a username to find their Steam profile")
async def steamfind(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed steamfind command - username:{username}")
    
    embed = build_steamfind_embed(username)

    await interaction.edit_original_response(embed=embed)


@tree.command(name="monitor", description="Add a player to be monitored from Battlemetrics ID")
async def monitor(interaction: discord.Interaction, battlemetrics_id: str):
    await interaction.response.defer()

    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed monitor command - battlemetrics_id:{battlemetrics_id}")

    server_data = get_online_server(battlemetrics_id)
    player_data = get_battlemetrics_player(battlemetrics_id)
    player_name = player_data['data']['attributes']['name']

    battlemetrics_ids.add(battlemetrics_id)
    save_monitored_ids(battlemetrics_ids)

    if not server_data:
        recently_visited = get_recently_visited_servers(battlemetrics_id, 5)
        
        embed = discord.Embed(
            title=f"Player Status: {player_name}",
            description=f"`{player_name}` ({battlemetrics_id}) is currently offline.",
            color=discord.Color.red()
        )
        
        for server in reversed(recently_visited):
            last_seen = datetime.fromisoformat(server['lastSeen'].replace('Z', '+00:00'))
            discord_timestamp = int(last_seen.replace(tzinfo=timezone.utc).timestamp())
            
            embed.add_field(
                name=f"🖥️ Server: {server['name']}",
                value=f"🆔 ID: `{server['id']}`\n"
                      f"⏰ Last Seen: <t:{discord_timestamp}:f> (<t:{discord_timestamp}:R>)\n"
                      f"🔗 [View Server](https://battlemetrics.com/servers/rust/{server['id']})",
                inline=False
            )
        
        embed.set_footer(text="Recently visited servers (up to 5) • Player added to persistent monitoring • Made by seall.dev", icon_url="https://seall.dev/images/logo.png")
        
        await interaction.edit_original_response(embed=embed)
    else:
        await send_activity_embed(interaction.channel, server_data.get('id', ''), battlemetrics_id, True)
        await interaction.edit_original_response(content="Player status has been posted above. Player added to persistent monitoring.")


@tree.command(name="monitorrm", description="Remove a player from being monitored")
async def monitorrm(interaction: discord.Interaction, battlemetrics_id: str):
    await interaction.response.defer()

    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed monitorrm command - battlemetrics_id:{battlemetrics_id}")

    if battlemetrics_id in battlemetrics_ids:
        battlemetrics_ids.remove(battlemetrics_id)
        save_monitored_ids(battlemetrics_ids)
        player_data = get_battlemetrics_player(battlemetrics_id)
        player_name = player_data['data']['attributes']['name']

        embed = discord.Embed(
            title="Player Monitoring Removed",
            description=f"`{player_name}` ({battlemetrics_id}) has been removed from monitoring.",
            color=discord.Color.blue()
        )

        embed.set_footer(text="Player will no longer be tracked and has been removed from persistent storage")

        await interaction.edit_original_response(embed=embed)
    else:
        embed = discord.Embed(
            title="Player Not Found",
            description=f"Player with ID `{battlemetrics_id}` was not being monitored.",
            color=discord.Color.orange()
        )

        await interaction.edit_original_response(embed=embed)

@tree.command(name="personahistory", description="Get persona history for a Steam ID")
async def personahistory(interaction: discord.Interaction, steam_id: str):
    await interaction.response.defer()

    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed personahistory command - steam_id:{steam_id}")
    
    url = f"https://steamhistory.net/id/{steam_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await interaction.followup.send(f"Error: Unable to fetch data for Steam ID '`{steam_id}`'")
                return
                
            html = await response.text()
            if 'does not exist!</p>' in html and '<p>ID: ' in html:
                await interaction.followup.send(f"Error: Steam ID '`{steam_id}`' does not exist.")
            soup = BeautifulSoup(html, 'html.parser')
            persona_table = soup.find('h1', string='Persona History').find_next('table')
            if not persona_table:
                await interaction.followup.send(f"No persona history found for Steam ID {steam_id}")
                return
                
            persona_history = []
            for row in persona_table.find_all('tr')[1:]:
                columns = row.find_all('td')
                if len(columns) == 2:
                    name = columns[0].text.strip()
                    time_str = columns[1].text.strip()
                    estimated = False
                    if 'Estimated' in time_str:
                        estimated = True
                        time_str = time_str.split(' [Estimated')[0]
                    time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    timestamp = int(time.replace(tzinfo=timezone.utc).timestamp())
                    persona_history.append((name, timestamp, estimated))

            pages = []
            entries_per_page = 10
            total_entries = len(persona_history)

            img_tag = soup.find('img', id='userimage')

            if img_tag:
                profile_picture_url = img_tag.get('src')
            
            for i in range(0, total_entries, entries_per_page):
                page_entries = persona_history[i:i + entries_per_page]
                description = ""
                
                for name, timestamp, estimated in page_entries:
                    entry = f"**{name}** 👤\nTimestamp ⏰ <t:{timestamp}:f> (<t:{timestamp}:R>)"
                    if estimated:
                        entry += "\n[Estimated Timestamp]"
                    entry += "\n\n"
                    description += entry
                
                embed = discord.Embed(
                    title=f"Persona History for Steam ID: {steam_id}",
                    url=url,
                    color=discord.Color.blue(),
                    description=description
                )
                


                embed.set_thumbnail(url=profile_picture_url)

                start_entry = i + 1
                end_entry = min(i + entries_per_page, total_entries)
                embed.set_footer(text=f"Page {len(pages) + 1} • Entries {start_entry}-{end_entry} of {total_entries} • Made by seall.dev", 
                        icon_url="https://seall.dev/images/logo.png")
                
                pages.append(embed)

            if not pages:
                await interaction.followup.send("No entries found.")
                return

            view = HistoryPaginationView(pages)
            view.message = await interaction.followup.send(embed=pages[0], view=view)

@tree.command(name="search", description="Search for a player on BattleMetrics")
@app_commands.describe(username="The username of the player", access_token="Your BattleMetrics access token (optional)")
@app_commands.choices(game=[
    app_commands.Choice(name="Rust", value="rust"),
    app_commands.Choice(name="None", value="none")
])
async def search(interaction: discord.Interaction, username: str, game: app_commands.Choice[str], access_token: str = None):
    global seen_ids
    await interaction.response.defer()

    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed search command - username:{username} game:{game} access_token:{access_token}")

    selected_game = game.value

    results = []
    sort_methods = ["", "-lastSeen", "firstSeen"]

    for method in sort_methods:
        new_results, error = await search_player(username, method, seen_ids, selected_game, access_token, interaction)
        if error:
            await interaction.edit_original_response(content=f"❌ Error: {error}")
            return
        results.extend(new_results)

    if ' ' in username:
        for method in sort_methods:
            new_results, error = await search_player(username.replace(' ', '+'), method, seen_ids, selected_game, access_token, interaction)
            if error:
                await interaction.edit_original_response(content=f"❌ Error: {error}")
                return
            results.extend(new_results)

    if not results:
        await interaction.edit_original_response(content="🔍 No exact matches found.")
        return

    sorted_results = sorted(results, key=lambda x: x['last_seen'], reverse=True)[:100]

    pages = []
    entries_per_page = 5
    total_entries = len(sorted_results)

    for i in range(0, total_entries, entries_per_page):
        page_entries = sorted_results[i:i + entries_per_page]

        embed = create_embed(
            title="🎮 BattleMetrics Search Results",
            description=f"🔍 Search results for: **{username}**\n"
        )

        if access_token:
            embed.description += "🔐 Access Token authentication used.\n"

        embed.description += "\n"

        for result in page_entries:
            last_seen = datetime.fromisoformat(result['last_seen'].replace('Z', '+00:00'))
            discord_timestamp = int(last_seen.replace(tzinfo=timezone.utc).timestamp())

            user_info = (
                f"**{result['username']}** 👤\n"
                f"🆔 ID: `{result['id']}`\n"
                f"⏰ Last Seen: <t:{discord_timestamp}:f> (<t:{discord_timestamp}:R>)\n"
                f"🔗 [View Profile](https://www.battlemetrics.com/players/{result['id']})\n\n"
            )
            embed.description += user_info

        start_entry = i + 1
        end_entry = min(i + entries_per_page, total_entries)
        embed.set_footer(text=f"Page {len(pages) + 1} • Entries {start_entry}-{end_entry} of {total_entries} • Made by seall.dev",
                         icon_url="https://seall.dev/images/logo.png")

        pages.append(embed)

    if not pages:
        await interaction.edit_original_response(content="🔍 No results to display.")
        return

    view = SearchPaginationView(pages)

    view.message = await interaction.edit_original_response(content=None, embed=pages[0], view=view)

    seen_ids = set()

@tree.command(name="correlate", description="Find overlapping sessions for multiple players")
async def correlate(interaction: discord.Interaction, player_ids: str, days: int = 30, access_token: Optional[str] = None):
    await interaction.response.defer()
    
    # Log command execution
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    server_id = interaction.guild.id if interaction.guild else "DM"
    channel_id = interaction.channel.id if interaction.channel else "N/A"
    user_id = interaction.user.id
    print(f"[{timestamp}] Server: {server_id}, Channel: {channel_id}, User: {user_id} - Executed correlate command - player_ids:{player_ids} days:{days} access_token:{access_token}")

    player_list = player_ids.split(',')
    player_names = {}
    i=0
    for player_id in player_list:
        i+=1
        await interaction.edit_original_response(content=f"Getting player names {i}/{len(player_list)}...")
        player_data = get_battlemetrics_player(player_id)
        player_name = player_data['data']['attributes']['name']
        player_names[player_id] = player_name
    
    await interaction.edit_original_response(content="Starting session correlation...")
    
    overlapping_sessions = await find_overlapping_sessions(player_list, player_names, days, access_token, interaction=interaction)
    
    if not overlapping_sessions:
        await interaction.edit_original_response(
            content=f"🔍 No overlapping sessions found in the last {days} days."
        )
        return

    view = CorrelationPaginationView(
        overlapping_sessions=overlapping_sessions,
        player_names=player_names,
        days=days,
        access_token=bool(access_token)
    )
    
    message = await interaction.edit_original_response(
        content=None,
        embed=view.pages[0],
        view=view
    )
    
    view.message = message

@tasks.loop(seconds=10)
async def monitor_loop():
    global battlemetrics_json_data, user_status, battlemetrics_ids, monitor_channel_id
    try:
        channel = await client.fetch_channel(monitor_channel_id)
        if not channel:
            print(f"Error: Could not find channel with ID {monitor_channel_id}")
            return
        for battlemetrics_id in battlemetrics_ids:
            player_data = get_battlemetrics_player(battlemetrics_id)
            player_name = player_data.get('data', {}).get('attributes', {}).get('name', 'Unknown Player')
            server_data = get_online_server(battlemetrics_id)
            online_status = bool(server_data)

            if battlemetrics_id not in user_status:
                user_status[battlemetrics_id] = {'online': False, 'serverid': '0'}

            if (user_status[battlemetrics_id]['online'] == False and online_status == True) or \
            (user_status[battlemetrics_id]['online'] == True and online_status == False):
                await send_activity_embed(channel, server_data.get('id', ''), battlemetrics_id, online_status)
                user_status[battlemetrics_id]['online'] = not user_status[battlemetrics_id]['online']
                user_status[battlemetrics_id]['serverid'] = server_data.get('id', '0')
            elif online_status == True and user_status[battlemetrics_id]['online'] == True and \
                user_status[battlemetrics_id]['serverid'] != server_data['id']:
                await send_serverchange_embed(channel, server_data.get('id', ''), battlemetrics_id)
                user_status[battlemetrics_id]['serverid'] = server_data.get('id', '0')
    except Exception as e:
        print(f"Error in monitor_loop: {e}")
    battlemetrics_json_data = None

@monitor_loop.before_loop
async def before_monitor_loop():
    await client.wait_until_ready()

if __name__ == "__main__":
    # Get the token from the .env file
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("No token found. Make sure to set DISCORD_BOT_TOKEN in your .env file.")
    
    client.run(TOKEN)