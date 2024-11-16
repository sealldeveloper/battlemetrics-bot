import json
usernames = []

def load_usernames():
    """ Todo """
    global usernames
    with open("data/RandomUsernames.json") as f:
        usernames = json.loads(f.read())["RandomUsernames"]
    return


def get_streamermode_name(steam_id: str):
    """ Todo """
    global usernames
    """Code used from https://github.com/NotpainRaov/RustStreamerName/blob/master/main.py"""
    if len(usernames) == 0:
        load_usernames()
    
    index = int(steam_id) % 2147483647
    index = index % len(usernames)

    return usernames[index]
    