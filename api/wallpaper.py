from http.server import BaseHTTPRequestHandler
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import json
import os
import io

WIDTH = 1170
HEIGHT = 2532
BG_COLOR = (13, 13, 13)
QUOTE_COLOR = (255, 255, 255)
AUTHOR_COLOR = (140, 140, 140)
ACCENT_COLOR = (80, 80, 80)
DATE_COLOR = (60, 60, 60)


def load_quotes():
    quotes_path = os.path.join(os.path.dirname(__file__), '..', 'quotes.json')
    with open(quotes_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_font(size):
    font_path = os.path.join(os.path.dirname(__file__), '..', 'Merriweather_24pt-Regular.ttf')
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines, current_line = [], []
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
