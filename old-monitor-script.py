#!/usr/bin/env python3
"""
Battlemetrics Player Monitor

A tool for monitoring player activity on game servers using the Battlemetrics API.
This script can track when players join/leave servers and provide notifications
through Discord webhooks. It supports continuous monitoring of multiple players
and provides detailed server information.

Original author: sealldev / sealldeveloper
Some code adapted from: alexemanuelol's 'team-detector' (GitHub)
"""

from tabulate import tabulate
import argparse
import json
import requests
import sys
from datetime import datetime
from time import sleep
from dotenv import load_dotenv
import os
from util import (
    get_battlemetrics_player,
    get_online_server,
    get_battlemetrics_server_details,
    get_recently_visited_servers
)

load_dotenv()

debug = False
battlemetrics_json_data = None
user_status = {}
webhook_url = os.getenv('WEBHOOK_URL')


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
        if battlemetrics_json_data is None:
            content = get_request(f'https://api.battlemetrics.com/players/{battlemetrics_player_id}?include=server')
            if not content:
                sys.exit('Failed to retrieve player data')
            battlemetrics_json_data = json.loads(content)

        debug_print(f'get_battlemetrics_player(battlemetrics_player_id:{battlemetrics_player_id}) -> '
                   f'Dict[data:{len(battlemetrics_json_data["data"])},included:{len(battlemetrics_json_data["included"])}]')
        return battlemetrics_json_data
    except Exception as e:
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


def send_activity_embed(server_id: str, battlemetrics_player_id: str, online_status: bool) -> None:
    """
    Send a Discord embed notification for player status changes.

    Creates and sends a detailed embed notification when a player goes online or offline,
    including server information and join commands when applicable.

    Args:
        server_id (str): The Battlemetrics server ID (empty string if player is offline).
        battlemetrics_player_id (str): The Battlemetrics player ID.
        online_status (bool): True if player is online, False if offline.

    Raises:
        SystemExit: If there's an error creating or sending the embed.
    """
    global user_status, webhook_url
    try:
        player_data = get_battlemetrics_player(battlemetrics_player_id)
        if server_id:
            server_details = get_battlemetrics_server_details(server_id)
            join_url = f"https://sealldeveloper.github.io/steam-uri-http-proxy/?ip={server_details['ip']}&port={server_details['port']}"

        embed = {}
        if online_status:
            embed['title'] = f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) is Online :green_circle:"
            embed['description'] = f"**Console Join Command**: `connect {server_details['ip']}:{server_details['port']}`\n[**Steam URI Redirect**]({join_url}) (Only works when game is closed)" if join_url else "Player is online."
            embed['color'] = 5763719  # Green
            embed['image'] = {'url': f"https://cdn.battlemetrics.com/b/horizontal500x80px/{server_id}.png?foreground=%23EEEEEE&background=%23222222&lines=%23333333&linkColor=%231185ec&chartColor=%23FF0700"}
            embed['fields'] = [
                {
                    "name": f"**Server:** `{server_details['name']}` ({server_id})",
                    "value": f"""
                        **Players:** `{server_details['players']}/{server_details['maxPlayers']}`
                        **Server Type:** `{server_details['serverType']}`
                        **URL:** `{server_details['URL']}`
                        **World Size:** `{server_details['worldSize']}`
                        **Queued Players:** `{server_details['queue']}`
                        **Server Steam ID:** `{server_details['steamId']}`
                        **Description:** ```
                        {server_details['description']}
                        ```
                        """
                }
            ]
            if server_details['headerImageURL']:
                embed['thumbnail'] = {'url': server_details['headerImageURL']}
        else:
            embed['title'] = f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) is Offline :red_circle:"
            embed['description'] = "No longer on any server."
            embed['color'] = 15548997  # Red

        embed['footer'] = {
            "text": "Created by sealldev",
            "icon_url": "https://seall.dev/images/logo.png"
        }

        send_embed(embed)
    except Exception as e:
        sys.exit(e)


def send_serverchange_embed(server_id: str, battlemetrics_player_id: str) -> None:
    """
    Send a Discord embed notification when a player changes servers.

    Creates and sends a notification with information about the new server
    when a player switches servers without going offline first.

    Args:
        server_id (str): The Battlemetrics ID of the new server.
        battlemetrics_player_id (str): The Battlemetrics player ID.

    Raises:
        SystemExit: If there's an error creating or sending the embed.
    """
    global user_status, webhook_url
    try:
        player_data = get_battlemetrics_player(battlemetrics_player_id)
        if server_id != '':
            server_details = get_battlemetrics_server_details(server_id)
            join_url = f"https://sealldeveloper.github.io/steam-uri-http-proxy/?ip={server_details['ip']}&port={server_details['port']}"
        embed = {}
        embed['title'] = f"`{player_data['data']['attributes']['name']}` ({battlemetrics_player_id}) has changed servers! :yellow_circle:"
        embed['description'] = f"**Console Join Command**: `connect {server_details['ip']}:{server_details['port']}`\n[**Steam URI Redirect**]({join_url}) (Only works when game is closed)" if join_url else "Player is online."
        embed['color'] = 15844367
        embed['image'] = {'url':f"https://cdn.battlemetrics.com/b/horizontal500x80px/{server_id}.png?foreground=%23EEEEEE&background=%23222222&lines=%23333333&linkColor=%231185ec&chartColor=%23FF0700"}
        embed['fields'] = [
                {
                    "name": f"**Server:** `{server_details['name']}` ({server_id})",
                    "value": f"**Players:** `{server_details['players']}/{server_details['maxPlayers']}`",
                }
            ]
        embed['footer'] = {
                "text": "Created by sealldev",
                "icon_url": "https://seall.dev/images/logo.png"
            }

        send_embed(embed)
    except Exception as e:
        sys.exit(e)

def main():
    global debug, user_status, battlemetrics_json_data
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-b', '--battlemetrics-ids', type=str, nargs='+', required=True, help='BattleMetrics Player IDs.')
    parser.add_argument('-l', '--loop', action='store_true', required=False, help='Enables the script to recursively check.')
    parser.add_argument('-d', '--debug', action='store_true', required=False, help='Enables debug print.')
    args = parser.parse_args()

    battlemetrics_ids = args.battlemetrics_ids
    debug = args.debug
    loop = args.loop

    if battlemetrics_ids == None:
        sys.exit('BattleMetrics Player ID is not provided.')

    if debug:
        print('Running with the following arguments:')
        print(f' - BattleMetrics Player IDs:   {battlemetrics_ids}')
        print(f' - Loop:                        {loop}')
        print(f' - Debug:                       {debug}')
        print()

    if loop:
        for battlemetrics_id in battlemetrics_ids:
            user_status[battlemetrics_id] = {'online':False,'serverid':'0'}
        while True:
            for battlemetrics_id in battlemetrics_ids:
                player_data = get_battlemetrics_player(battlemetrics_id)
                player_name = player_data.get('data', {}).get('attributes', {}).get('name', 'Unknown Player')
                server_data = get_online_server(battlemetrics_id)
                online_status = bool(server_data)
                if (user_status[battlemetrics_id]['online'] == False and online_status == True) or (user_status[battlemetrics_id]['online'] == True and online_status == False):
                    send_activity_embed(server_data.get('id', ''), battlemetrics_id, online_status)
                    user_status[battlemetrics_id]['online'] = not user_status[battlemetrics_id]['online']
                    user_status[battlemetrics_id]['serverid'] = server_data.get('id', '0')
                elif online_status == True and user_status[battlemetrics_id]['online'] == True and user_status[battlemetrics_id]['serverid'] != server_data['id']:
                    send_serverchange_embed(server_data.get('id',''), battlemetrics_player_id)
                    user_status[battlemetrics_id]['serverid'] = server_data.get('id', '0')
                battlemetrics_json_data = None
            sleep(20)
    else:
        for battlemetrics_id in battlemetrics_ids:
            server_data = get_online_server(battlemetrics_id)
            if server_data == None:
                recently_visited = get_recently_visited_servers(battlemetrics_id,5)

                processed_servers = []
                for server in recently_visited:
                    processed_server = {k: v for k, v in server.items() if k != 'online'}
                    processed_server['url'] = f"https://battlemetrics.com/servers/rust/{str(server['id'])}" 
                    processed_servers.append(processed_server)
                
                print(tabulate(processed_servers, headers='keys', tablefmt='grid'))
                print()
                print()

if __name__ == '__main__':
    print("Python script entry point reached")
    main()
