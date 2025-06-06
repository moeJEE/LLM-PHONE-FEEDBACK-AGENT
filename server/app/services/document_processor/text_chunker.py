from typing import List, Dict, Any

class TextChunker:
    """Split document text into smaller chunks for processing"""
    
    @staticmethod
    def chunk_document(document: Dict[str, Any], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Split a document into chunks with optional overlap
        
        Args:
            document: Dictionary with 'content' and 'metadata' keys
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            
        Returns:
            List of dictionaries with 'content' and 'metadata' keys, where content is a chunk of the original text
        """
        text = document["content"]
        metadata = document["metadata"]
        
        # Split text into chunks
        if len(text) <= chunk_size:
            return [{"content": text, "metadata": metadata}]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find the end of this chunk
            end = start + chunk_size
            
            # If we're not at the end of the document, try to find a natural break point
            if end < len(text):
                # Try to find a paragraph break
                paragraph_break = text.rfind("\n\n", start, end)
                if paragraph_break != -1 and paragraph_break > start + chunk_size // 2:
                    end = paragraph_break + 2  # Include the double newline
                else:
                    # Try to find a single newline
                    newline = text.rfind("\n", start, end)
                    if newline != -1 and newline > start + chunk_size // 2:
                        end = newline + 1  # Include the newline
                    else:
                        # Try to find the end of a sentence
                        for sep in [". ", "! ", "? "]:
                            sentence_end = text.rfind(sep, start, end)
                            if sentence_end != -1 and sentence_end > start + chunk_size // 2:
                                end = sentence_end + 2  # Include the separator
                                break
            
            # Extract the chunk
            chunk = text[start:end]
            
            # Create chunk-specific metadata
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = len(chunks)
            chunk_metadata["chunk_start_char"] = start
            chunk_metadata["chunk_end_char"] = end
            
            chunks.append({"content": chunk, "metadata": chunk_metadata})
            
            # Move the start pointer for the next chunk, accounting for overlap
            start = end - chunk_overlap
        
        return chunks