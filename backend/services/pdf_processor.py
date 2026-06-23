import pypdf
from typing import List, Dict, Any

def process_pdf(filepath: str) -> List[Dict[str, Any]]:
    """
    Parses a PDF file, extracts text page by page, and returns chunks.
    Each chunk is a dictionary containing:
      - 'content': the text content of the chunk
      - 'page_number': the 1-based page number where the text resides
      - 'chunk_index': sequence index of the chunk
    """
    chunks = []
    chunk_idx = 0
    
    try:
        reader = pypdf.PdfReader(filepath)
        total_pages = len(reader.pages)
        
        for page_num in range(total_pages):
            page = reader.pages[page_num]
            text = page.extract_text()
            
            if not text or not text.strip():
                continue
                
            # Chunk the page text
            # Industrial documents need accurate page citations.
            # We split the page text into smaller paragraphs/sections if it's large,
            # but keep them associated with the exact page.
            max_chunk_size = 1000
            overlap = 200
            
            page_text = text.strip()
            
            if len(page_text) <= max_chunk_size:
                chunks.append({
                    "content": page_text,
                    "page_number": page_num + 1,
                    "chunk_index": chunk_idx
                })
                chunk_idx += 1
            else:
                # Sliding window chunking within the page
                start = 0
                while start < len(page_text):
                    end = start + max_chunk_size
                    chunk_content = page_text[start:end]
                    
                    chunks.append({
                        "content": chunk_content,
                        "page_number": page_num + 1,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    
                    start += (max_chunk_size - overlap)
                    
    except Exception as e:
        print(f"Error processing PDF {filepath}: {e}")
        
    return chunks
