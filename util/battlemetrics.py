from util.general import get_request
import json
import sys
import requests
from time import sleep
import os
import random
from datetime import datetime
from urllib.parse import urlencode, quote_plus

battlemetrics_json_data = None
user_status = {}
battlemetrics_ids = []

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
        
        # Clear previous data to avoid stale cache
        battlemetrics_json_data = None
        
        content = get_request(f'https://api.battlemetrics.com/players/{battlemetrics_player_id}?include=server')
        if not content:
            sys.exit('Failed to retrieve player data')
        
        battlemetrics_json_data = json.loads(content)
        
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
        servers = get_battlemetrics_player_servers(battlemetrics_player_id)
        recently_visited_servers = servers[-n:]
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
        servers = get_battlemetrics_player_servers(battlemetrics_player_id)

        for server in servers:
            if server['online']:
                return server
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
        content = get_request(f'https://api.battlemetrics.com/servers/{server_id}')
        if not content:
            sys.exit('Failed to retrieve server data')
        content = json.loads(content)

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
        return server_details
    except Exception as e:
        sys.exit(e)


async def get_player_sessions(player_id, player_names, start_time, end_time, jwt=None, ignore_jwt=False, interaction=None):
    """ Todo """
    count = 1
    url = f"https://api.battlemetrics.com/sessions"
    params = {
        "include": "server",
        "page[size]": 90,
        "filter[players]": player_id,
    }
    
    if jwt and not ignore_jwt:
        params["access_token"] = jwt

    url += f"?{urlencode(params, quote_via=quote_plus)}"
    sessions = []
    
    while url:
        if interaction:
            await interaction.edit_original_response(content=f"Fetching sessions for player {player_names[player_id]} ({player_id})... Page #{count}")
        
        response = requests.get(url)
        if response.status_code == 401 and not ignore_jwt:
            return await get_player_sessions(player_id, player_names, start_time, end_time, ignore_jwt=True, interaction=interaction)
        if response.status_code != 200:
            return []

        data = response.json()
        sessions.extend(data['data'])
        
        if 'links' in data:
            url = data['links'].get('next')
            if url and jwt and not ignore_jwt:
                url += f"&access_token={jwt}"
            count += 1
        else:
            url = None

    return sessions