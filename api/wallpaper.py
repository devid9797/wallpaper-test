from http.server import BaseHTTPRequestHandler
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import json
import os
import io
import textwrap

# iPhone 14/15 Pro resolution
WIDTH = 1170
HEIGHT = 2532

# Colors
BG_COLOR = (13, 13, 13)         # #0D0D0D
QUOTE_COLOR = (255, 255, 255)   # white
AUTHOR_COLOR = (140, 140, 140)  # grey
ACCENT_COLOR = (80, 80, 80)     # subtle accent for decorative line
DATE_COLOR = (60, 60, 60)       # very subtle date


def load_quotes():
    quotes_path = os.path.join(os.path.dirname(__file__), '..', 'quotes.json')
    with open(quotes_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_font(size, bold=False):
    """Try to load a system font, fall back to default."""
    font_candidates = [
        # macOS / Linux common paths
        '/System/Library/Fonts/Supplemental/Georgia.ttf',
        '/System/Library/Fonts/Georgia.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
        # Vercel Lambda layer
        '/var/lang/lib/python3.9/site-packages/PIL/fonts/FreeMono.ttf',
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fallback to PIL default (bitmap)
    return ImageFont.load_default()


def wrap_text(text, font, draw, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []

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


def generate_wallpaper(quote_text: str, author: str, day_of_year: int, total_days: int) -> bytes:
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Subtle gradient overlay (manual, pixel rows)
    for y in range(HEIGHT):
        alpha = int(y / HEIGHT * 18)  # 0 → 18 darkness gradient
        r = max(0, BG_COLOR[0] - alpha)
        g = max(0, BG_COLOR[1] - alpha)
        b = max(0, BG_COLOR[2] - alpha)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    padding = 100
    text_area_width = WIDTH - padding * 2

    # Fonts
    quote_font = get_font(76)
    author_font = get_font(42)
    date_font = get_font(32)

    # Wrap quote text
    quote_lines = wrap_text(f'\u201c{quote_text}\u201d', quote_font, draw, text_area_width)

    # Measure total quote block height
    line_spacing = 24
    line_height = quote_font.getbbox('Hy')[3] - quote_font.getbbox('Hy')[1]
    quote_block_height = len(quote_lines) * (line_height + line_spacing) - line_spacing

    # Measure author height
    author_line_height = author_font.getbbox('Hy')[3] - author_font.getbbox('Hy')[1]

    gap_between = 60  # between quote and author
    total_content_height = quote_block_height + gap_between + author_line_height

    # Center vertically (slightly above center — feels more balanced on phone)
    start_y = (HEIGHT - total_content_height) // 2 - 80

    # Draw thin accent line above quote
    line_x1 = padding
    line_x2 = padding + 80
    line_y = start_y - 48
    draw.line([(line_x1, line_y), (line_x2, line_y)], fill=ACCENT_COLOR, width=2)

    # Draw quote lines
    current_y = start_y
    for line in quote_lines:
        draw.text((padding, current_y), line, font=quote_font, fill=QUOTE_COLOR)
        current_y += line_height + line_spacing

    # Draw author — right-aligned
    author_text = f'— {author}'
    author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_width = author_bbox[2] - author_bbox[0]
    author_x = WIDTH - padding - author_width
    author_y = current_y + gap_between - line_spacing
    draw.text((author_x, author_y), author_text, font=author_font, fill=AUTHOR_COLOR)

    # Draw day-of-year progress dots near bottom
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

    # Day label
    day_text = f'день {day_of_year}'
    day_bbox = draw.textbbox((0, 0), day_text, font=date_font)
    day_x = (WIDTH - (day_bbox[2] - day_bbox[0])) // 2
    draw.text((day_x, dots_y + 28), day_text, font=date_font, fill=DATE_COLOR)

    # Export to bytes
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
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
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
        pass  # suppress default logging
