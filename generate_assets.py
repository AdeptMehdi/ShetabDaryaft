from PIL import Image, ImageDraw, ImageFont
import os

def create_directory_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_logo():
    # Create a directory for assets if it doesn't exist
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    create_directory_if_not_exists(assets_dir)
    
    # Create a logo image
    img_width, img_height = 200, 200
    img = Image.new('RGBA', (img_width, img_height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a circle
    circle_center = (img_width // 2, img_height // 2)
    circle_radius = 80
    
    # Draw gradient-like circles
    for i in range(circle_radius, 0, -2):
        # Calculate color - blue to cyan gradient
        r = int(41 * (1 - i/circle_radius))
        g = int(128 + 127 * (1 - i/circle_radius))
        b = int(185 + 70 * (1 - i/circle_radius))
        
        draw.ellipse(
            [(circle_center[0] - i, circle_center[1] - i), 
             (circle_center[0] + i, circle_center[1] + i)], 
            fill=(r, g, b, 255)
        )
    
    # Draw downward arrow
    arrow_width = 30
    arrow_height = 60
    arrow_top = circle_center[1] - arrow_height // 2
    arrow_left = circle_center[0] - arrow_width // 2
    
    # Draw arrow shape
    arrow_points = [
        (circle_center[0], arrow_top + arrow_height),  # Bottom point
        (arrow_left, arrow_top + arrow_height // 2),   # Left point
        (circle_center[0] - arrow_width // 4, arrow_top + arrow_height // 2),  # Left inner
        (circle_center[0] - arrow_width // 4, arrow_top),  # Top left
        (circle_center[0] + arrow_width // 4, arrow_top),  # Top right
        (circle_center[0] + arrow_width // 4, arrow_top + arrow_height // 2),  # Right inner
        (arrow_left + arrow_width, arrow_top + arrow_height // 2),  # Right point
    ]
    
    draw.polygon(arrow_points, fill=(255, 255, 255, 230))
    
    # Save the logo
    logo_path = os.path.join(assets_dir, "logo.png")
    img.save(logo_path)
    
    # Create icon version (with transparency)
    icon_path = os.path.join(assets_dir, "icon.ico")
    img.save(icon_path, format='ICO', sizes=[(32, 32), (64, 64), (128, 128)])
    
    print(f"Created logo at {logo_path}")
    print(f"Created icon at {icon_path}")

if __name__ == "__main__":
    generate_logo()
