"""
Generate favicon for Torrent2Drive webapp.
This creates a simple but recognizable favicon.
"""
from PIL import Image, ImageDraw
import os

# Create a 512x512 image with transparency
size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background color - Apple blue
bg_color = (0, 122, 255, 255)

# Draw rounded rectangle background
def draw_rounded_rectangle(draw, xy, corner_radius, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + corner_radius, y1, x2 - corner_radius, y2], fill=fill)
    draw.rectangle([x1, y1 + corner_radius, x2, y2 - corner_radius], fill=fill)
    draw.pieslice([x1, y1, x1 + corner_radius * 2, y1 + corner_radius * 2], 180, 270, fill=fill)
    draw.pieslice([x2 - corner_radius * 2, y1, x2, y1 + corner_radius * 2], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - corner_radius * 2, x1 + corner_radius * 2, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - corner_radius * 2, y2 - corner_radius * 2, x2, y2], 0, 90, fill=fill)

# Draw background
draw_rounded_rectangle(draw, [0, 0, size, size], 80, bg_color)

# Draw cloud shape (simplified)
cloud_color = (255, 255, 255, 255)

# Main cloud body
draw.ellipse([120, 180, 320, 320], fill=cloud_color)
draw.ellipse([200, 140, 380, 280], fill=cloud_color)
draw.ellipse([250, 160, 420, 300], fill=cloud_color)
draw.ellipse([140, 200, 280, 340], fill=cloud_color)

# Draw upload arrow
arrow_color = (0, 122, 255, 255)

# Arrow shaft
draw.rectangle([236, 260, 276, 380], fill=arrow_color)

# Arrow head
arrow_head = [
    (256, 200),
    (200, 270),
    (236, 270),
    (236, 280),
    (276, 280),
    (276, 270),
    (312, 270),
]
draw.polygon(arrow_head, fill=arrow_color)

# Draw small circle at bottom (torrent symbol)
circle_color = (52, 199, 89, 255)
draw.ellipse([236, 400, 276, 440], fill=circle_color, outline=(255, 255, 255, 255), width=6)

# Save as different sizes
output_dir = 'webapp/static'
os.makedirs(output_dir, exist_ok=True)

# Save original size
img.save(os.path.join(output_dir, 'favicon-512.png'))

# Save common favicon sizes
for icon_size in [16, 32, 64, 180, 192]:
    resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    if icon_size == 16:
        resized.save(os.path.join(output_dir, 'favicon.ico'))
    resized.save(os.path.join(output_dir, f'favicon-{icon_size}.png'))

# Save Apple touch icon
apple_icon = img.resize((180, 180), Image.Resampling.LANCZOS)
apple_icon.save(os.path.join(output_dir, 'apple-touch-icon.png'))

print("Favicon generated successfully!")
print("  - favicon.ico (16x16)")
print("  - favicon-16.png")
print("  - favicon-32.png")
print("  - favicon-64.png")
print("  - favicon-192.png (Android)")
print("  - favicon-512.png")
print("  - apple-touch-icon.png (180x180)")
