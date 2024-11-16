import requests
import sys
import json

from util.battlemetrics import (
    get_battlemetrics_player, 
    get_battlemetrics_server_details,

)


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