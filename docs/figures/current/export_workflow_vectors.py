"""Export the native workflow PDF at 180 mm width, retaining its 3:2 layout."""
from pathlib import Path
import fitz

OUT=Path(__file__).resolve().parent
source=fitz.open(OUT/'workflow-native.pdf')
target=fitz.open()
page=target.new_page(width=180/25.4*72,height=120/25.4*72)
page.show_pdf_page(page.rect,source,0)
target.save(OUT/'figure_1_workflow.pdf')
page.get_pixmap(dpi=600).save(OUT/'figure_1_workflow.png')
(OUT/'figure_1_workflow.svg').write_text(page.get_svg_image(text_as_path=False),encoding='utf-8')
target.close();source.close()
print('Workflow PDF, SVG and 600 dpi PNG preserve the original 3:2 aspect ratio.')
