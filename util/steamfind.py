from urllib.parse import urlencode, quote_plus
import discord
from util.general import get_steam_avatar

def build_steamfind_embed(username: str):
    """ Todo """
    base_google = "https://www.google.com/search?"
    
    queries = {
        # Steam Dorks
        "steamcommunityfiltered": f'site:steamcommunity.com "{username}" -inurl:/groups -inurl:/friends -inurl:/games -inurl:/inventory -inurl:/screenshots -inurl:/allcomments -inurl:/myworkshopfiles -inurl:/stats -inurl:/sharedfiles -inurl:/market -inurl:/discussions',
        "steamcommunity": f'site:steamcommunity.com "{username}"',
        "steamhistory": f'site:steamhistory.net "{username}"',
        "exophase": f'site:exophase.com "{username}" AND "Profile"',
        "steamidfinder": f'site:steamidfinder.com "{username}"',
        "steamhunters": f'site:steamhunters.com "{username}"',
        "steamladder": f'site:steamladder.com "{username}"',
        "steamrep": f'site:steamrep.com "{username}"',
        "steamcollector": f'site:steamcollector.com "{username}"',
        "steamidpro": f'site:steamid.pro "{username}"',
        "battlemetrics": f'site:battlemetrics.com "{username}"',

        # Rocket League Dorks
        "ballchasing": f'site:ballchasing.com "{username}"',

        # CS2 Dorks
        "fplleaderboards": f'site:fplleaderboards.com "{username}"',
        "faceit": f'site:faceit.com "{username}"',
        "faceitfinder": f'site:faceitfinder.com "{username}" AND "profile"',
        "settingsgg": f'site:settings.gg "{username}"',

        # Deadlock Dorks
        "tracklockgg": f'site:tracklock.gg "{username}"',

        # TF2 Dorks
        "backpacktf": f'site:backpack.tf "{username}"',
        "scraptf": f'site:scrap.tf "{username}"',
        "stntradingeu": f'site:stntrading.eu "{username}"',
        "trendstf": f'site:trends.tf "{username}"',
        "logstf": f'site:logs.tf "{username}"',
        "demostf": f'site:demos.tf "{username}"',
        "rglgg": f'site:rgl.gg "{username}"',
        "etf2l": f'site:etf2l.org "{username}"',
        "ugcleague": f'site:ugcleague.com "{username}"',
        "cltf2": f'site:cltf2.com "{username}"',
        "ozfortress": f'site:ozfortress.com "{username}"'
    }

    dorks = {name: base_google + urlencode({'q': query}, quote_via=quote_plus) for name, query in queries.items()}
    
    steam_dork = "https://steamcommunity.com/search/users/#" + urlencode({'text': username}, quote_via=quote_plus)

    embed = discord.Embed(
        title=f"Google Dorks for {username}",
        description=(
            "**Steam Dorks:**\n"
            f"[steamcommunity.com Dork]({dorks['steamcommunity']})\n"
            f"[steamcommunity.com Filtered Dork]({dorks['steamcommunityfiltered']})\n"
            f"[steamhistory.net Dork]({dorks['steamhistory']})\n"
            f"[exophase.com Dork]({dorks['exophase']})\n"
            f"[steamidfinder.com Dork]({dorks['steamidfinder']})\n"
            f"[steamhunters.com Dork]({dorks['steamhunters']})\n"
            f"[steamladder.com Dork]({dorks['steamladder']})\n"
            f"[steamrep.com Dork]({dorks['steamrep']})\n"
            f"[steamcollector.com Dork]({dorks['steamcollector']})\n"
            f"[steamid.pro Dork]({dorks['steamidpro']})\n"
            f"[battlemetrics.com Dork]({dorks['battlemetrics']})\n"
            f"[Steam Search]({steam_dork}) :warning: very bad matching for common usernames or usernames with spaces\n\n"

            "**Rocket League Dork:**\n"
            f"[ballchasing.com Dork]({dorks['ballchasing']})\n\n"

            "**CS2 Dorks:**\n"
            f"[fplleaderboards.com Dork]({dorks['fplleaderboards']})\n"
            f"[faceit.com Dork]({dorks['faceit']})\n"
            f"[faceitfinder.com Dork]({dorks['faceitfinder']})\n"
            f"[settings.gg Dork]({dorks['settingsgg']})\n\n"

            "**Deadlock Dorks:**\n"
            f"[tracklock.gg Dork]({dorks['tracklockgg']})\n\n"

            "**TF2 Dorks:**\n"
            f"[backpack.tf Dork]({dorks['backpacktf']})\n"
            f"[scrap.tf Dork]({dorks['scraptf']})\n"
            f"[stntrading.eu Dork]({dorks['stntradingeu']})\n"
            f"[trendstf Dork]({dorks['trendstf']})\n"
            f"[logs.tf Dork]({dorks['logstf']})\n"
            f"[demos.tf Dork]({dorks['demostf']})\n"
            f"[rgl.gg Dork]({dorks['rglgg']})\n"
            f"[etf2l.org Dork]({dorks['etf2l']})\n"
            f"[ugcleague.com Dork]({dorks['ugcleague']})\n"
            f"[cltf2.com Dork]({dorks['cltf2']})\n"
            f"[ozfortress.com Dork]({dorks['ozfortress']})\n"
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(text="Made by seall.dev", icon_url="https://seall.dev/images/logo.png")

    return embed
