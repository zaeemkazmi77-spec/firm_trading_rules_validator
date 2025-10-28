import pdfplumber

# Open the PDF file
pdf_path = 'Project_Plan.pdf'
output_path = 'Project_Plan.txt'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages in PDF: {len(pdf.pages)}")
    
    # Extract text from all pages
    all_text = []
    for i, page in enumerate(pdf.pages, 1):
        text = page.extract_text()
        if text:
            all_text.append(f"--- Page {i} ---\n{text}")
            print(f"Extracted page {i}")
        else:
            print(f"Warning: Page {i} has no text")
    
    # Write to file
    full_text = '\n\n'.join(all_text)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"\n✅ PDF converted successfully!")
    print(f"Output saved to: {output_path}")
    print(f"Total characters extracted: {len(full_text)}")
