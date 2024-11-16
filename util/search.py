import requests
from urllib.parse import urlencode, quote_plus
BASE_URL = "https://api.battlemetrics.com"

async def search_player(username, sort_method, seen_ids, game=None, jwt=None, interaction=None):
    """ Todo """
    base_url = f"{BASE_URL}/players"
    params = {
        "page[size]": 90,
        "sort": sort_method,
        "filter[search]": username,
        "filter[playerFlags]": "",
        "include": "flagPlayer,playerFlag,server"
    }

    if jwt:
        params['access_token'] = jwt
    if game and game != 'none':
        params['filter[server][game]'] = game
    
    all_results = []
    current_url = f"{base_url}?{urlencode(params, quote_via=quote_plus)}"
    headers = {}
    page_count = 0
    while current_url and len(all_results) < 100:
        page_count += 1
        try:
            if interaction:
                if sort_method == '':
                    sort_method = 'relevance'
                await interaction.edit_original_response(content=f"Searching for `{username}` with method `{sort_method}`... Page {page_count}")

            response = requests.get(current_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            for player in data['data']:
                player_id = player['id']
                if player['attributes']['name'] == username and player_id not in seen_ids:
                    seen_ids.add(player_id)
                    if len(player['relationships']['servers']['data']) > 0:
                        all_results.append({
                            'username': player['attributes']['name'],
                            'id': player_id,
                            'last_seen': player['relationships']['servers']['data'][0]['meta']['lastSeen']
                        })
                
                if len(all_results) >= 100:
                    break

            next_url = data['links'].get('next')
            current_url = next_url if next_url and len(all_results) < 100 else None

        except requests.exceptions.RequestException as e:
            error = f"Error occurred while fetching data: {e}".replace(jwt,'')
            if interaction:
                await interaction.edit_original_response(content=error)
            return [], error

    if interaction:
        await interaction.edit_original_response(content=f"🔍 Search completed. Found {len(all_results)} results.")
    
    return all_results, None