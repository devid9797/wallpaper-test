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
    font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Merriweather_24pt-Regular.ttf')
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
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines


def generate_wallpaper(quote_text, author, day_of_year, total_days):
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    padding = 100
    text_area_width = WIDTH - padding * 2

    quote_font = get_font(76)
    author_font = get_font(42)
    date_font = get_font(32)

    quote_lines = wrap_text(f'\u201c{quote_text}\u201d', quote_font, draw, text_area_width)

    line_spacing = 24
    line_height = quote_font.getbbox('Hy')[3] - quote_font.getbbox('Hy')[1]
    quote_block_height = len(quote_lines) * (line_height + line_spacing) - line_spacing
    author_line_height = author_font.getbbox('Hy')[3] - author_font.getbbox('Hy')[1]
    gap_between = 60
    total_content_height = quote_block_height + gap_between + author_line_height

    start_y = (HEIGHT - total_content_height) // 2 - 80

    line_y = start_y - 48
    draw.line([(padding, line_y), (padding + 80, line_y)], fill=ACCENT_COLOR, width=2)

    current_y = start_y
    for line in quote_lines:
        draw.text((padding, current_y), line, font=quote_font, fill=QUOTE_COLOR)
        current_y += line_height + line_spacing

    author_text = f'— {author}'
    author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_width = author_bbox[2] - author_bbox[0]
    author_x = WIDTH - padding - author_width
    author_y = current_y + gap_between - line_spacing
    draw.text((author_x, author_y), author_text, font=author_font, fill=AUTHOR_COLOR)

    dots_y = HEIGHT - 160
    dot_r = 5
    dot_gap = 22
    total_dots = 12
    filled_dots = max(1, round((day_of_year / total_days) * total_dots))
    total_dots_width = total_dots * dot_r * 2 + (total_dots - 1) * dot_gap
    dots_x_start = (WIDTH - total_dots_width) // 2

    for i in range(total_dots):
        cx = dots_x_start + i * (dot_r * 2 + dot_gap) + dot_r
        color = (180, 180, 180) if i < filled_dots else (45, 45, 45)
        draw.ellipse([(cx - dot_r, dots_y - dot_r), (cx + dot_r, dots_y + dot_r)], fill=color)

    day_text = f'день {day_of_year}'
    day_bbox = draw.textbbox((0, 0), day_text, font=date_font)
    day_x = (WIDTH - (day_bbox[2] - day_bbox[0])) // 2
    draw.text((day_x, dots_y + 28), day_text, font=date_font, fill=DATE_COLOR)

    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf.read()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            quotes = load_quotes()
            now = datetime.now()
            day_of_year = now.timetuple().tm_yday
            total_days = 366 if (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)) else 365
            quote = quotes[day_of_year % len(quotes)]
            image_bytes = generate_wallpaper(
                quote_text=quote['text'],
                author=quote['author'],
                day_of_year=day_of_year,
                total_days=total_days,
            )
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(image_bytes)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(image_bytes)
        except Exception as e:
            error_msg = f'Error: {str(e)}'.encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(error_msg)))
            self.end_headers()
            self.wfile.write(error_msg)

    def log_message(self, format, *args):
        pass
