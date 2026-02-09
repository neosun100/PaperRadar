from app.services.pdf_builder import PDFBuilder

def test_builder():
    builder = PDFBuilder()
    
    # Mock page data
    page = {
        "width": 600,
        "height": 800,
        "images": [],
        "text_blocks": [
            {
                "bbox": [50, 50, 550, 150], # Top of page
                "rewritten_text": "<h1>This is a Title parsed from tags</h1>",
                "text": "Original Title",
                "style": "body", # Should be overridden to h1
                "is_bold": True
            },
            {
                "bbox": [50, 200, 300, 400],
                "rewritten_text": "<h2>Section Header from tags</h2><br/>This is a longer paragraph that should wrap automatically because we are using ReportLab Paragraph flowable. " * 5,
                "text": "Original Body",
                "style": "body"
            },
            {
                "bbox": [50, 450, 300, 500],
                "rewritten_text": "<caption>Figure 1: This is a figure caption parsed from tags</caption>",
                "text": "Original Caption",
                "style": "body" # Should be overridden to caption
            },
            {
                "bbox": [50, 450, 300, 500],
                "rewritten_text": "This is a caption.",
                "text": "Original",
                "style": "caption"
            }
        ],
        "links": [],
        "page_index": 0
    }

    # Page 2: Reflow Test
    # Block 1 expands significantly. Block 2 (Image/Text) should be pushed down.
    page2 = {
        "width": 600,
        "height": 800,
        "images": [
            {
                "bbox": [50, 300, 250, 400], # Originally at Y=300-400
                "data": b"", # Mock data, won't render but will be reflowed
                "type": "image"
            }
        ],
        "text_blocks": [
            {
                "bbox": [50, 50, 550, 100], # Height 50.
                # Text is long enough to expand beyond 50px height with standard font.
                "rewritten_text": "<h1>Reflow Test Title</h1>" + ("<br/>This is a long paragraph that should expand the text block height significantly. " * 10),
                "text": "Short Original",
                "style": "body"
            },
            {
                "bbox": [50, 150, 550, 200], # Originally at Y=150. Should be pushed down by Block 1.
                "rewritten_text": "This block should be pushed down.",
                "text": "Original Block 2",
                "style": "body"
            }
        ],
        "links": [],
        "page_index": 1
    }
    
    doc_layout = {"pages": [page, page2]}
    
    try:
        pdf_bytes = builder.build(doc_layout)
        print(f"Successfully generated PDF of size: {len(pdf_bytes)} bytes")
        with open("test_render.pdf", "wb") as f:
            f.write(pdf_bytes)
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_builder()
