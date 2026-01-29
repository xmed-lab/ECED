import os
from glob import glob
from PyPDF2 import PdfReader, PdfWriter


def split_pdf(input_pdf_path, max_pages=600):
    input_pdf = PdfReader(input_pdf_path)
    total_pages = len(input_pdf.pages)

    if total_pages <= max_pages:
        print(f"The PDF has {total_pages} pages, no need to split.")
        return

    output_dir = os.path.dirname(input_pdf_path)
    base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]

    for i in range(0, total_pages, max_pages):
        output_pdf_path = os.path.join(output_dir, f"{base_name}_part_{i // max_pages + 1}.pdf")
        if os.path.exists(output_pdf_path):
            print(f"{output_pdf_path} already exists, skipping...")
            continue
        output_pdf = PdfWriter()
        for j in range(i, min(i + max_pages, total_pages)):
            output_pdf.add_page(input_pdf.pages[j])
        with open(output_pdf_path, "wb") as output_file:
            output_pdf.write(output_file)

        print(f"Created: {output_pdf_path}")


if __name__ == "__main__":
    all_books = glob("../RawBooks/*.pdf")  # Replace with your PDF folder path
    for book in all_books:
        split_pdf(book)