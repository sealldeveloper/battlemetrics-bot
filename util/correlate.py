from datetime import datetime, timedelta
import requests
import pytz
from util.battlemetrics import get_player_sessions


async def find_overlapping_sessions(player_ids, player_names, days_back, jwt=None, ignore_jwt=False, interaction=None):
    """ Todo """
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
