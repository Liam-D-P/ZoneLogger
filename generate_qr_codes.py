import qrcode
import os
from PIL import Image, ImageDraw, ImageFont
import requests
from pathlib import Path

# Define zone mapping directly in this script
zone_mapping = {
    "zone123abc": "Engineering Misson",
    "zone456def": "Developer Control Plane",
    "zone789ghi": "Harness & Backstage",
    "zone012jkl": "DevOps",
    "zone345mno": "Quality Engineering",
    "zone678pqr": "Engineering Experience",
    "zone901stu": "Whack a Mole Challenge",
    "zone234vwx": "Cloud Mission",
    "zone567yza": "How Cloud Can Help",
    "zone890bcd": "Cloud Adoption",
    "zone321efg": "Voice of a Customer",
    "zone654hij": "Chat Bot Demo"
}

def download_poppins_font():
    """Download Poppins font if not already present"""
    font_path = Path("Poppins-Regular.ttf")
    if not font_path.exists():
        url = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf"
        response = requests.get(url)
        font_path.write_bytes(response.content)
    return str(font_path)

def generate_qr_code(data):
    """Generate a QR code with embedded logo and return the image"""
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    
    # Add data
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create QR code image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_image = qr_image.convert('RGBA')
    
    # Open and resize logo
    logo = Image.open("Images/Reboot24_logo.jpg")
    logo = logo.convert('RGBA')
    
    # Calculate logo size (about 25% of QR code size)
    logo_size = qr_image.size[0] // 4
    logo = logo.resize((logo_size, logo_size))
    
    # Create a white background for the logo
    white_bg = Image.new('RGBA', logo.size, 'white')
    white_bg.paste(logo, (0, 0), logo)
    logo = white_bg
    
    # Calculate position to center logo
    pos = ((qr_image.size[0] - logo.size[0]) // 2,
           (qr_image.size[1] - logo.size[1]) // 2)
    
    # Paste logo onto QR code
    qr_image.paste(logo, pos, logo)
    
    return qr_image

def create_combined_image():
    # Calculate grid size (4x3 for 12 zones)
    rows, cols = 3, 4
    # Size of each QR code plus some padding
    qr_size = 150
    padding = 20
    text_height = 40  # Increased height for text
    
    # Create a new white image with extra height for text
    cell_height = qr_size + text_height + padding
    combined_width = cols * (qr_size + padding) + padding
    combined_height = rows * cell_height + padding
    combined_image = Image.new('RGB', (combined_width, combined_height), 'white')
    draw = ImageDraw.Draw(combined_image)
    
    # Try to load Poppins font, fall back to default if not available
    try:
        font_path = download_poppins_font()
        font = ImageFont.truetype(font_path, 14)  # Slightly larger font size
    except:
        font = ImageFont.load_default()
    
    # Generate and paste QR codes with labels
    for i, (zone_id, zone_name) in enumerate(zone_mapping.items()):
        # Generate QR code
        qr_image = generate_qr_code(zone_id)
        qr_image = qr_image.resize((qr_size, qr_size))
        
        # Calculate position
        row = i // cols
        col = i % cols
        x = col * (qr_size + padding) + padding
        y = row * cell_height + padding
        
        # Paste QR code
        combined_image.paste(qr_image, (x, y))
        
        # Add zone name text
        text_width = draw.textlength(zone_name, font=font)
        text_x = x + (qr_size - text_width) // 2  # Center text under QR code
        text_y = y + qr_size + 10  # Position text below QR code
        draw.text((text_x, text_y), zone_name, fill="black", font=font)
    
    return combined_image

def main():
    # Create output directory if it doesn't exist
    output_dir = "qr_codes"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate combined image
    combined_image = create_combined_image()
    
    # Save the combined image
    output_path = f"{output_dir}/all_zones_qr_codes.png"
    combined_image.save(output_path, "PNG")
    print(f"Generated combined QR codes image at: {output_path}")

if __name__ == "__main__":
    main()