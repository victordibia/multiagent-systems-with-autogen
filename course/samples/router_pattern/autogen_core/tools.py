import uuid
import requests
from fpdf import FPDF
from typing import List, Dict, Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from io import BytesIO
import unicodedata
import io, base64
from openai import OpenAI
 

def generate_pdf_report(
    sections: List[Dict[str, Optional[str]]], 
    output_file: str = "report.pdf", 
    report_title: str = "PDF Report"
) -> None:
    def normalize_text(text: str) -> str:
        """Normalize Unicode text to ASCII."""
        return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

    def get_image(image_url_or_path):
        """Fetch image from URL or local path."""
        if image_url_or_path.startswith(("http://", "https://")):
            response = requests.get(image_url_or_path)
            if response.status_code == 200:
                return BytesIO(response.content)
        elif Path(image_url_or_path).is_file():
            return open(image_url_or_path, 'rb')
        return None

    def add_rounded_corners(img, radius=6):
        """Add rounded corners to an image."""
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), img.size], radius, fill=255)
        img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        img.putalpha(mask)
        return img

    class PDF(FPDF):
        """Custom PDF class with header and content formatting."""
        def header(self):
            self.set_font("Arial", "B", 12)
            # Normalize the report title
            normalized_title = normalize_text(report_title)
            self.cell(0, 10, normalized_title, 0, 1, "C")
            
        def chapter_title(self, txt): 
            self.set_font("Arial", "B", 12)
            # Normalize the title text
            normalized_txt = normalize_text(txt)
            self.cell(0, 10, normalized_txt, 0, 1, "L")
            self.ln(2)
        
        def chapter_body(self, body):
            self.set_font("Arial", "", 12)
            # Normalize the body text
            normalized_body = normalize_text(body)
            self.multi_cell(0, 10, normalized_body)
            self.ln()

        def add_image(self, img_data):
            img = Image.open(img_data)
            img = add_rounded_corners(img)
            img_path = Path(f"temp_{uuid.uuid4().hex}.png")
            img.save(img_path, format="PNG")
            self.image(str(img_path), x=None, y=None, w=190 if img.width > 190 else img.width)
            self.ln(10)
            img_path.unlink()

    # Initialize PDF
    pdf = PDF()
    pdf.add_page()
    font_size = {"title": 16, "h1": 14, "h2": 12, "body": 12}

    # Add sections
    for section in sections:
        title = section.get("title", "")
        level = section.get("level", "h1")
        content = section.get("content", "")
        image = section.get("image")

        pdf.set_font("Arial", "B" if level in font_size else "", font_size.get(level, font_size["body"]))
        pdf.chapter_title(title)

        if content:
            pdf.chapter_body(content)
        
        if image:
            img_data = get_image(image)
            if img_data:
                pdf.add_image(img_data)
                if isinstance(img_data, BytesIO):
                    img_data.close()

    pdf.output(output_file)
    print(f"PDF report saved as {output_file}")



def generate_images(query: str, output_dir: Path = None, image_size: str = "1024x1024") -> List[str]:
    """
    Generate and save images based on a text description using OpenAI's DALL-E model.
    
    Args:
        query: A natural language description of the image to be generated
        output_dir: Directory to save the images (default: current directory)
        image_size: The size of the image to be generated (default: "1024x1024")
    
    Returns:
        List[str]: A list of paths for the saved images
    
    Note:
        Requires a valid OpenAI API key set in your environment variables
    """
    # Initialize the OpenAI client
    client = OpenAI()
    
    # Generate images using DALL-E 3
    response = client.images.generate(
        model="dall-e-3",
        prompt=query,
        n=1,
        response_format="b64_json",
        size=image_size
    )

    saved_files = []
 
    # Process the response
    if response.data:
        for image_data in response.data:
            # Generate a unique filename
            file_name = f"{uuid.uuid4()}.png"
            
            # Use output_dir if provided, otherwise use current directory
            file_path = Path(output_dir) / file_name if output_dir else Path(file_name)

            base64_str = image_data.b64_json 
            img = Image.open(io.BytesIO(base64.decodebytes(bytes(base64_str, "utf-8")))) 

            # Save the image to a file 
            img.save(file_path)  

            saved_files.append(str(file_path))
             
    else:
        print("No image data found in the response!")

    return saved_files