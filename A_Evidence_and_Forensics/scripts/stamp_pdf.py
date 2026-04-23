import sys
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import red
    from pypdf import PdfReader, PdfWriter
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "reportlab", "pypdf"])
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import red
    from pypdf import PdfReader, PdfWriter

import os

input_pdf = "1517SanJuan-new-floorplan.pdf"
output_pdf = "1517SanJuan-new-floorplan-DIMENSIONS.pdf"
watermark_pdf = "temp_stamp.pdf"

# Read original to get dimensions
reader = PdfReader(input_pdf)
page = reader.pages[0]
width = float(page.mediabox.width)
height = float(page.mediabox.height)

# Create the stamp
c = canvas.Canvas(watermark_pdf, pagesize=(width, height))
c.setFillColor(red)
c.setFont("Helvetica-Bold", 14)

# We will place the text towards the bottom center-right
start_x = width * 0.4
start_y = height * 0.25

c.drawString(start_x, start_y, "NEW ENTRYWAY DIMS:")
c.setFont("Helvetica", 12)
c.drawString(start_x, start_y - 15, "Back Wall (door): 100\"")
c.drawString(start_x, start_y - 30, "Left Wall (garage): 111\"")
c.drawString(start_x, start_y - 45, "Right Wall (master): 76\"")
c.drawString(start_x, start_y - 60, "Soffit Width: 24\"")
c.save()

# Merge the watermark
watermark = PdfReader(watermark_pdf).pages[0]
writer = PdfWriter()

for idx, page in enumerate(reader.pages):
    if idx == 0:
        page.merge_page(watermark)
    writer.add_page(page)

with open(output_pdf, "wb") as output:
    writer.write(output)

os.remove(watermark_pdf)
print(f"Successfully stamped {output_pdf}")
