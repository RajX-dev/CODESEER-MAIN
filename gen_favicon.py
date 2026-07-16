from PIL import Image, ImageDraw

def create_favicon(size, filename):
    # Transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    scale = size / 130.0
    
    tl = (30 * scale, 20 * scale)
    bl = (30 * scale, 110 * scale)
    br = (110 * scale, 110 * scale)
    tr = (110 * scale, 20 * scale)
    
    color = "#f59e0b" # Orange
    line_width = max(1, int(14 * scale))
    
    # Draw N lines
    draw.line([bl, tl, br, tr], fill=color, width=line_width, joint="curve")
    
    # Draw nodes
    r = 7 * scale
    circle_color = "#ffffff"
    circle_outline = "#f59e0b"
    circle_width = max(1, int(4 * scale))
    
    for pt in [tl, bl, br, tr]:
        x, y = pt
        bbox = [x - r, y - r, x + r, y + r]
        draw.ellipse(bbox, fill=circle_color, outline=circle_outline, width=circle_width)
        
    img.save(filename)

# Make 192x192 PNG for standard Android/Chrome favicon
create_favicon(192, "public/icon-192x192.png")
# Make 180x180 for apple touch icon
create_favicon(180, "public/apple-touch-icon.png")

# Make ICO with multiple sizes
img_48 = Image.open("public/icon-192x192.png").resize((48, 48), Image.Resampling.LANCZOS)

img_48.save("public/favicon.ico", format="ICO", sizes=[(48, 48), (32, 32), (16, 16)])

print("Favicons generated successfully!")
