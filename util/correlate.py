from datetime import datetime, timedelta
import requests
import pytz
from urllib.parse import urlencode, quote_plus

BASE_URL = "https://api.battlemetrics.com"

async def find_overlapping_sessions(player_ids, player_names, days_back, jwt=None, ignore_jwt=False, interaction=None):
    end_time = datetime.now(pytz.UTC)
    start_time = end_time - timedelta(days=days_back)

    all_sessions = {}
    for i, player_id in enumerate(player_ids):
        if interaction:
            await interaction.edit_original_response(content=f"Fetching sessions for player {i+1}/{len(player_ids)}...")
        all_sessions[player_id] = await get_player_sessions(player_id, player_names, start_time, end_time, jwt, ignore_jwt, interaction)

    if interaction:
        await interaction.edit_original_response(content="Analyzing overlapping sessions...")

    overlapping_sessions = []

    for i in range(len(player_ids)):
        for j in range(i + 1, len(player_ids)):
            player1_sessions = all_sessions[player_ids[i]]
            player2_sessions = all_sessions[player_ids[j]]

            for session1 in player1_sessions:
                start1 = datetime.fromisoformat(session1['attributes']['start'].replace('Z', '+00:00'))
                stop1 = datetime.fromisoformat(session1['attributes']['stop'].replace('Z', '+00:00')) if session1['attributes']['stop'] else end_time
                server1 = session1['relationships']['server']['data']['id']

                for session2 in player2_sessions:
                    start2 = datetime.fromisoformat(session2['attributes']['start'].replace('Z', '+00:00'))
                    stop2 = datetime.fromisoformat(session2['attributes']['stop'].replace('Z', '+00:00')) if session2['attributes']['stop'] else end_time
                    server2 = session2['relationships']['server']['data']['id']

                    if server1 == server2 and max(start1, start2) < min(stop1, stop2):
                        overlap_start = max(start1, start2)
                        overlap_stop = min(stop1, stop2)
                        duration = overlap_stop - overlap_start
                        
                        existing_overlap = next((o for o in overlapping_sessions 
                                              if o['server_id'] == server1 and 
                                              o['start'] == overlap_start and 
                                              o['stop'] == overlap_stop), None)

                        if existing_overlap:
                            if player_ids[j] not in existing_overlap['players']:
                                existing_overlap['players'].append(player_ids[j])
                        else:
                            overlapping_sessions.append({
                                'server_id': server1,
                                'start': overlap_start,
                                'stop': overlap_stop,
                                'duration': duration,
                                'players': [player_ids[i], player_ids[j]]
                            })

    return overlapping_sessions

async def get_player_sessions(player_id, player_names, start_time, end_time, jwt=None, ignore_jwt=False, interaction=None):
    count = 1
    url = f"{BASE_URL}/sessions"
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