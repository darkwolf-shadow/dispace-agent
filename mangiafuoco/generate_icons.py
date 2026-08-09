from PIL import Image, ImageDraw
import os, json

repo = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(repo, 'www', 'bot-avatar.png')
img = Image.open(src).convert('RGBA')

def circular_avatar(size, padding_ratio=0.08, bg_color=None):
    """Return a size x size icon with the avatar cropped to a circle."""
    out = Image.new('RGBA', (size, size), bg_color or (0, 0, 0, 0))
    thumb = img.copy()
    thumb = thumb.resize((size, size), Image.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    pad = int(size * padding_ratio)
    radius = size // 2 - pad
    draw.ellipse((pad, pad, size - pad, size - pad), fill=255)
    out.paste(thumb, (0, 0), mask)
    return out

def square_with_circle(size, bg_color=(217, 79, 14, 255)):
    """Square icon with rounded-corners feel: a circle on a colored background."""
    out = Image.new('RGBA', (size, size), bg_color)
    pad = size // 12
    radius = size // 2 - pad
    thumb = img.copy().resize((size - 2*pad, size - 2*pad), Image.LANCZOS)
    mask = Image.new('L', (size - 2*pad, size - 2*pad), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 2*pad, size - 2*pad), fill=255)
    out.paste(thumb, (pad, pad), mask)
    return out

# Web icons
web_dir = os.path.join(repo, 'www')
favicon = circular_avatar(64, padding_ratio=0.0)
favicon.save(os.path.join(web_dir, 'favicon.png'))

touch = circular_avatar(180, padding_ratio=0.0)
touch.save(os.path.join(web_dir, 'apple-touch-icon.png'))

icon192 = circular_avatar(192, padding_ratio=0.0)
icon192.save(os.path.join(web_dir, 'icon-192.png'))

icon512 = circular_avatar(512, padding_ratio=0.0)
icon512.save(os.path.join(web_dir, 'icon-512.png'))

manifest = {
    "name": "Mangiafuoco",
    "short_name": "Mangiafuoco",
    "start_url": ".",
    "display": "standalone",
    "background_color": "#fff8f0",
    "theme_color": "#d94f0e",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}
    ]
}
with open(os.path.join(web_dir, 'manifest.json'), 'w') as f:
    json.dump(manifest, f, indent=2)

# Android launcher icons
android_res = os.path.join(repo, 'android', 'app', 'src', 'main', 'res')
legacy_sizes = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
fg_sizes = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}

for density, size in legacy_sizes.items():
    d = os.path.join(android_res, f'mipmap-{density}')
    square_with_circle(size).save(os.path.join(d, 'ic_launcher.png'))
    circular_avatar(size, padding_ratio=0.0, bg_color=(217, 79, 14, 255)).save(os.path.join(d, 'ic_launcher_round.png'))

for density, size in fg_sizes.items():
    d = os.path.join(android_res, f'mipmap-{density}')
    # adaptive foreground: circle with ~25% padding so it sits in the safe zone
    fg = circular_avatar(size, padding_ratio=0.22)
    fg.save(os.path.join(d, 'ic_launcher_foreground.png'))

print('Icons generated.')
