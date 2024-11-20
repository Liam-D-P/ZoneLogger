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
    "zone345mno": "Quality Engineering - Reboot Challenge",
    "zone678pqr": "Engineering Experience",
    "zone901stu": "Whack a Mole Challenge",
    "zone234vwx": "Cloud Mission",
    "zone567yza": "How Cloud Can Help",
    "zone846fgh": "Cloud Enable",
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

def generate_qr_code(data, zone_name):
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
    
    # Create a new image with space for text
    padding = 20
    text_height = 40
    final_image = Image.new('RGB', 
                           (qr_image.size[0] + 2*padding, 
                            qr_image.size[1] + text_height + 2*padding), 
                           'white')
    
    # Paste QR code
    final_image.paste(qr_image, (padding, padding))
    
    # Add text
    draw = ImageDraw.Draw(final_image)
    try:
        font_path = download_poppins_font()
        font = ImageFont.truetype(font_path, 14)
    except:
        font = ImageFont.load_default()
    
    # Center text under QR code
    text_width = draw.textlength(zone_name, font=font)
    text_x = (final_image.size[0] - text_width) // 2
    text_y = qr_image.size[1] + padding + 10
    draw.text((text_x, text_y), zone_name, fill="black", font=font)
    
    return final_image

def main():
    # Create output directory if it doesn't exist
    output_dir = "qr_codes"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate individual QR codes for each zone
    for zone_id, zone_name in zone_mapping.items():
        # Generate QR code with zone name
        qr_image = generate_qr_code(zone_id, zone_name)
        
        # Clean the zone name to make it filesystem-friendly
        clean_name = zone_name.replace(" ", "_").replace("-", "_").replace("&", "and")
        
        # Save individual QR code using the zone name
        output_path = f"{output_dir}/{clean_name}.png"
        qr_image.save(output_path, "PNG")
        print(f"Generated QR code for {zone_name} at: {output_path}")

if __name__ == "__main__":
    main()