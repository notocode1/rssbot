# utils.py
import re
from bs4 import BeautifulSoup

def escape_markdown(text: str, version: int = 2) -> str:
    if not text:
        return ''
    if version == 2:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\\\\1', text)
    return text

def extract_image(entry):
    if 'media_content' in entry and entry.media_content:
        url = entry.media_content[0].get('url')
        if url and url.lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
            return url
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image'):
                return link.get('href')
    soup = BeautifulSoup(entry.get('summary', ''), 'html.parser')
    img = soup.find('img')
    if img and img.get('src') and img['src'].lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
        return img['src']
    return None
