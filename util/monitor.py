debug = False
user_status = {}
battlemetrics_json_data = None
battlemetrics_ids = []
monitor_channel_id = None
import requests
import sys
import json
from datetime import datetime
from time import sleep
import os
import random

async def send_activity_embed(channel, server_id: str, battlemetrics_player_id: str, online_status: bool) -> None:
    """
    Send a Discord embed notification for player status changes via the bot.

    Creates and sends a detailed embed notification when a player goes online or offline,
    including server information and join commands when applicable.

    Args:
        channel: The Discord channel to send the embed to.
        server_id (str): The Battlemetrics server ID (empty string if player is offline).
        battlemetrics_player_id (str): The Battlemetrics player ID.
        online_status (bool): True if player is online, False if offline.

    Raises:
        Exception: If there's an error creating or sending the embed.
    """
    try:
        player_data = get_battlemetrics_player(battlemetrics_player_id)
        
        if server_id:
            server_details = get_battlemetrics_server_details(server_id)
            join_url = f"https://sealldeveloper.github.io/steam-uri-http-proxy/?ip={server_details['ip']}&port={server_details['port']}"

            if online_status:
                embed = discord.Embed(
                    title=f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) is Online :green_circle:",
                    description=f"**Console Join Command**: `connect {server_details['ip']}:{server_details['port']}`\n[**Steam URI Redirect**]({join_url}) (Only works when game is closed)",
                    color=discord.Color.green()
                )
                embed.set_image(url=f"https://cdn.battlemetrics.com/b/horizontal500x80px/{server_id}.png?foreground=%23EEEEEE&background=%23222222&lines=%23333333&linkColor=%231185ec&chartColor=%23FF0700")
                embed.add_field(
                    name=f"**Server:** `{server_details['name']}` ({server_id})",
                    value=f"""
                    **Players:** `{server_details['players']}/{server_details['maxPlayers']}`
                    **Server Type:** `{server_details['serverType']}`
                    **URL:** `{server_details['URL']}`
                    **World Size:** `{server_details['worldSize']}`
                    **Queued Players:** `{server_details['queue']}`
                    **Server Steam ID:** `{server_details['steamId']}`
                    **Description:** ```{server_details['description']}```
                    """,
                    inline=False
                )
                if server_details['headerImageURL']:
                    embed.set_thumbnail(url=server_details['headerImageURL'])
            else:
                embed = discord.Embed(
                    title=f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) is Offline :red_circle:",
                    description="No longer on any server.",
                    color=discord.Color.red()
                )
        else:
            embed = discord.Embed(
                title=f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) is Offline :red_circle:",
                description="No longer on any server.",
                color=discord.Color.red()
            )

        embed.set_footer(text="Created by sealldev", icon_url="https://seall.dev/images/logo.png")
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error in send_activity_embed: {e}")
        raise

async def send_serverchange_embed(channel, server_id: str, battlemetrics_player_id: str) -> None:
    """
    Send a Discord embed notification when a player changes servers via the bot.

    Creates and sends a notification with information about the new server
    when a player switches servers without going offline first.

    Args:
        channel: The Discord channel to send the embed to.
        server_id (str): The Battlemetrics ID of the new server.
        battlemetrics_player_id (str): The Battlemetrics player ID.

    Raises:
        Exception: If there's an error creating or sending the embed.
    """
    try:
        player_data = get_battlemetrics_player(battlemetrics_player_id)
        if server_id:
            server_details = get_battlemetrics_server_details(server_id)
            join_url = f"https://sealldeveloper.github.io/steam-uri-http-proxy/?ip={server_details['ip']}&port={server_details['port']}"
            
            embed = discord.Embed(
                title=f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) has changed servers! :yellow_circle:",
                description=f"**Console Join Command**: `connect {server_details['ip']}:{server_details['port']}`\n[**Steam URI Redirect**]({join_url}) (Only works when game is closed)",
                color=discord.Color.yellow()
            )
            embed.set_image(url=f"https://cdn.battlemetrics.com/b/horizontal500x80px/{server_id}.png?foreground=%23EEEEEE&background=%23222222&lines=%23333333&linkColor=%231185ec&chartColor=%23FF0700")
            embed.add_field(
                name=f"**Server:** `{server_details['name']}` ({server_id})",
                value=f"**Players:** `{server_details['players']}/{server_details['maxPlayers']}`",
                inline=False
            )
            embed.set_footer(text="Created by sealldev", icon_url="https://seall.dev/images/logo.png")
            
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Error in send_serverchange_embed: {e}")
        raise

def debug_print(text: str) -> None:
    """
    Print debug information when debug mode is enabled.

    Args:
        text (str): The text message to be printed.
    """
    if debug:
        print(text)


def get_request(url: str) -> str:
    """
    Make a GET request to a specified URL with error handling.

    Args:
        url (str): The URL to send the GET request to.

    Returns:
        str: The response text from the request.

    Raises:
        ValueError: If the provided URL is empty or None.
        requests.exceptions.RequestException: If the HTTP request fails.
    """
    if not url:
        raise ValueError(f'URL cannot be empty or None. URL: {url}')

    try:
        debug_print(f'Requesting: {url}')
        headers={
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f'Could not request: {url}. Error: {e}')
        return ''


def get_battlemetrics_player(battlemetrics_player_id: str) -> dict:
    """
    Retrieve player information from the Battlemetrics API.
    
    Makes an API request to get player data including their current server status
    and caches the response to avoid redundant API calls.
    
    Args:
        battlemetrics_player_id (str): The Battlemetrics ID of the player.
    
    Returns:
        dict: JSON response containing player information and related server data.
    
    Raises:
        SystemExit: If the API request fails or returns invalid data.
    """
    global battlemetrics_json_data
    try:
        debug_print(f'get_battlemetrics_player(battlemetrics_player_id:{battlemetrics_player_id})')
        
        # Clear previous data to avoid stale cache
        battlemetrics_json_data = None
        
        content = get_request(f'https://api.battlemetrics.com/players/{battlemetrics_player_id}?include=server')
        if not content:
            sys.exit('Failed to retrieve player data')
        
        battlemetrics_json_data = json.loads(content)

        debug_print(f'get_battlemetrics_player(battlemetrics_player_id:{battlemetrics_player_id}) -> '
                    f'Dict[data:{len(battlemetrics_json_data["data"])},included:{len(battlemetrics_json_data["included"])}]')
        
        return battlemetrics_json_data
    except Exception as e:
        print(f"Error retrieving player data for ID {battlemetrics_player_id}: {e}")
        sys.exit(e)



def get_battlemetrics_player_servers(battlemetrics_player_id: str) -> list:
    """
    Retrieve and sort all servers a player has visited.

    Gets a list of all servers the player has connected to and sorts them
    by their last seen timestamp in ascending order.

    Args:
        battlemetrics_player_id (str): The Battlemetrics ID of the player.

    Returns:
        list: Sorted list of dictionaries containing server information:
            - name: Server name
            - id: Server ID
            - online: Current online status
            - lastSeen: Timestamp of last server connection

    Raises:
        SystemExit: If there's an error processing the server data.
    """
    try:
        debug_print(f'get_battlemetrics_player_servers(battlemetrics_player_id:{battlemetrics_player_id})')
        battlemetrics_json_data = get_battlemetrics_player(battlemetrics_player_id)

        servers = [
            {
                'name': server['attributes']['name'],
                'id': server['id'],
                'online': server['meta']['online'],
                'lastSeen': server['meta']['lastSeen']
            }
            for server in battlemetrics_json_data['included']
        ]
        
        sorted_servers = sorted(
            servers,
            key=lambda x: datetime.fromisoformat(x['lastSeen'].replace('Z', '+00:00'))
        )

        debug_print(f'get_battlemetrics_player_servers(battlemetrics_player_id:{battlemetrics_player_id}) -> '
                   f'List[servers:{len(sorted_servers)}]')
        return sorted_servers
    except Exception as e:
        sys.exit(e)


def get_recently_visited_servers(battlemetrics_player_id: str, n: int) -> list:
    """
    Get the n most recently visited servers for a player.

    Args:
        battlemetrics_player_id (str): The Battlemetrics ID of the player.
        n (int): Number of recent servers to return.

    Returns:
        list: The n most recently visited servers, sorted by last seen timestamp.

    Raises:
        SystemExit: If there's an error retrieving the server data.
    """
    try:
        debug_print(f'get_recently_visited_servers(battlemetrics_player_id:{battlemetrics_player_id}, n:{n})')
        servers = get_battlemetrics_player_servers(battlemetrics_player_id)
        recently_visited_servers = servers[-n:]
        debug_print(f'get_recently_visited_servers(battlemetrics_player_id:{battlemetrics_player_id}, n:{n}) -> '
                   f'List[recently_visited_servers:{len(recently_visited_servers)}]')
        return recently_visited_servers
    except Exception as e:
        sys.exit(e)


def get_online_server(battlemetrics_player_id: str) -> dict:
    """
    Check if a player is currently online and get their current server.

    Args:
        battlemetrics_player_id (str): The Battlemetrics ID of the player.

    Returns:
        dict: Server information if player is online, empty dict if offline.
            Server info includes:
            - name: Server name
            - id: Server ID
            - online: Current online status (True)
            - lastSeen: Timestamp of current session

    Raises:
        SystemExit: If there's an error checking the player's status.
    """
    try:
        debug_print(f'get_online_server(battlemetrics_player_id:{battlemetrics_player_id})')
        servers = get_battlemetrics_player_servers(battlemetrics_player_id)

        for server in servers:
            if server['online']:
                debug_print(f'get_online_server(battlemetrics_player_id:{battlemetrics_player_id}) -> '
                          f'Dict[name:"{server["name"]}"]')
                return server
        
        debug_print('Could not find user currently online.')
        return {}
    except Exception as e:
        sys.exit(e)


def get_battlemetrics_server(server_id: str) -> dict:
    """
    Retrieve detailed server information from the Battlemetrics API.

    Args:
        server_id (str): The Battlemetrics server ID.

    Returns:
        dict: Complete server information from the Battlemetrics API.

    Raises:
        SystemExit: If the API request fails or returns invalid data.
    """
    try:
        debug_print(f'get_battlemetrics_server(server_id:{server_id})')

        content = get_request(f'https://api.battlemetrics.com/servers/{server_id}')
        if not content:
            sys.exit('Failed to retrieve server data')
        content = json.loads(content)

        debug_print(f'get_battlemetrics_server(server_id:{server_id}) -> Dict[data:{len(content["data"])}]')
        return content
    except Exception as e:
        sys.exit(e)


def get_battlemetrics_server_details(server_id: str) -> dict:
    """
    Extract relevant server details from the Battlemetrics API response.

    Args:
        server_id (str): The Battlemetrics server ID.

    Returns:
        dict: Formatted server details including:
            - name: Server name
            - ip: Server IP address
            - port: Server port
            - players: Current player count
            - maxPlayers: Maximum players allowed
            - serverType: Type of server (e.g., rust_type)
            - headerImageURL: Server banner image URL
            - URL: Server's website URL
            - worldSize: Size of the game world
            - description: Server description
            - queue: Number of queued players
            - steamId: Server's Steam ID

    Raises:
        SystemExit: If there's an error processing the server details.
    """
    try:
        debug_print(f'get_battlemetrics_server_details(server_id:{server_id})')
        content = get_battlemetrics_server(server_id)

        server_details = {
            'name': content['data']['attributes']['name'],
            'ip': content['data']['attributes']['ip'],
            'port': content['data']['attributes']['port'],
            'players': content['data']['attributes']['players'],
            'maxPlayers': content['data']['attributes']['maxPlayers'],
            'serverType': content['data']['attributes']['details']['rust_type'],
            'headerImageURL': content['data']['attributes']['details']['rust_headerimage'],
            'URL': content['data']['attributes']['details']['rust_url'],
            'worldSize': content['data']['attributes']['details']['rust_worldsize'],
            'description': content['data']['attributes']['details']['rust_description'],
            'queue': content['data']['attributes']['details']['rust_queued_players'],
            'steamId': content['data']['attributes']['details']['serverSteamId']
        }

        debug_print(f'get_battlemetrics_server_details(server_id:{server_id}) -> '
                   f'Dict[server_details:{len(server_details)}]')
        return server_details
    except Exception as e:
        sys.exit(e)


def send_embed(embed: dict) -> None:
    """
    Send a Discord webhook embed notification.

    Args:
        embed (dict): The Discord embed object to send.

    Raises:
        SystemExit: If the webhook request fails.
    """
    try:
        payload = {"embeds": [embed]}
        response = requests.post(webhook_url, json=payload)

        if response.status_code == 204:
            print("Embed sent successfully")
        else:
            print(f"Failed to send embed. Status code: {response.status_code}")
            print(f"Response content: {response.text}")
    except Exception as e:
        sys.exit(e)