import requests
from bs4 import BeautifulSoup

def get_steam_avatar(steam_id):
    """ Todo """
    url = f"https://steamhistory.net/id/{steam_id}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
        
    html = response.content.decode()
    if 'does not exist!</p>' in html and '<p>ID: ' in html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    img_tag = soup.find('img', id='userimage')
    if img_tag:
        profile_picture_url = img_tag.get('src')
        return profile_picture_url

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