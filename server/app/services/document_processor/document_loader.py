import os
from typing import List, Union, Dict, Any
import pathlib

class DocumentLoader:
    """Load documents from various sources"""
    
    @staticmethod
    def load_file(file_path: Union[str, pathlib.Path]) -> Dict[str, Any]:
        """Load a single file and return its content and metadata"""
        if isinstance(file_path, str):
            file_path = pathlib.Path(file_path)
        
        extension = file_path.suffix.lower()
        
        # Get metadata
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "filetype": extension[1:],  # Remove the dot
            "size_bytes": os.path.getsize(file_path)
        }
        
        # Read content based on file type
        if extension == ".pdf":
            content = DocumentLoader._read_pdf(file_path)
        elif extension == ".docx":
            content = DocumentLoader._read_docx(file_path)
        elif extension == ".txt":
            content = DocumentLoader._read_text(file_path)
        elif extension in [".csv", ".xlsx", ".xls"]:
            content = DocumentLoader._read_tabular(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        
        return {"content": content, "metadata": metadata}
    
    @staticmethod
    def load_files(file_paths: List[Union[str, pathlib.Path]]) -> List[Dict[str, Any]]:
        """Load multiple files and return their contents and metadata"""
        documents = []
        for file_path in file_paths:
            documents.append(DocumentLoader.load_file(file_path))
        return documents
    
    @staticmethod
    def _read_pdf(file_path: pathlib.Path) -> str:
        """Extract text from a PDF file"""
        from pypdf import PdfReader
        
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    @staticmethod
    def _read_docx(file_path: pathlib.Path) -> str:
        """Extract text from a DOCX file"""
        import docx2txt
        return docx2txt.process(file_path)
    
    @staticmethod
    def _read_text(file_path: pathlib.Path) -> str:
        """Read a plain text file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    @staticmethod
    def _read_tabular(file_path: pathlib.Path) -> str:
        """Extract content from tabular data files (CSV, Excel)"""
        import pandas as pd
        
        extension = file_path.suffix.lower()
        if extension == '.csv':
            df = pd.read_csv(file_path)
        else:  # .xlsx or .xls
            df = pd.read_excel(file_path)
        
        # Convert DataFrame to a readable string format
        return df.to_string()