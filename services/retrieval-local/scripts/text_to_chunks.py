import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter   
from langchain_huggingface import HuggingFaceEmbeddings   

# Initialize the embedding model to get accurate token counts
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")

# Initialize the recursive character text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=480,
    chunk_overlap=100,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]
)

# Define base paths
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # retrieval-local folder
INPUT_FOLDER = BASE_DIR / "outputs" / "cleaned_text_output"
OUTPUT_FOLDER = BASE_DIR / "outputs" / "chunking_output"

def list_available_cleaned_files(input_folder):
    """
    List all available cleaned text files in the input folder.
    
    Args:
        input_folder (Path): Path to the folder containing cleaned text files
    
    Returns:
        list: List of cleaned text filenames (sorted)
    """
    if not input_folder.exists():
        print(f"Error: Input folder not found at {input_folder}")
        return []
    
    text_files = sorted([f.name for f in input_folder.glob('*.txt')])
    return text_files

def select_file(file_list):
    """
    Display available cleaned text files and let user select one.
    
    Args:
        file_list (list): List of available cleaned text filenames
    
    Returns:
        str: Selected text filename or None if invalid selection
    """
    if not file_list:
        print("No cleaned text files found in the input folder.")
        return None
    
    print("\n" + "="*50)
    print("Available Cleaned Text Files:")
    print("="*50)
    for idx, text_file in enumerate(file_list, 1):
        print(f"{idx}. {text_file}")
    
    print("\n" + "="*50)
    try:
        choice = int(input("Enter the file number to chunk (or 0 to cancel): "))
        if choice == 0:
            return None
        if 1 <= choice <= len(file_list):
            return file_list[choice - 1]
        else:
            print("Invalid selection. Please enter a valid file number.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

def load_cleaned_text(file_path):
    """Load the cleaned text from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None

def chunk_text(text):
    """Split text into chunks using RecursiveCharacterTextSplitter."""
    if not text or not text.strip():
        print("Warning: Empty or whitespace-only text provided")
        return []
    
    chunks = text_splitter.split_text(text)
    
    # Filter out very small or empty chunks
    filtered_chunks = [chunk.strip() for chunk in chunks if chunk.strip() and len(chunk.strip()) > 20]
    
    return filtered_chunks

def create_chunks_with_metadata(chunks):
    """Create chunks with metadata for cosine similarity operations."""
    chunks_data = []
    
    for idx, chunk in enumerate(chunks):
        chunk_obj = {
            "chunk_id": idx,
            "text": chunk,
            "length": len(chunk),
            "word_count": len(chunk.split()),
            "char_count": len(chunk)
        }
        chunks_data.append(chunk_obj)
    
    return chunks_data

def save_chunks_to_json(chunks_data, output_path):
    """Save chunks to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output_dict = {
        "total_chunks": len(chunks_data),
        "chunk_size": 480,
        "chunk_overlap": 100,
        "chunks": chunks_data
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully saved {len(chunks_data)} chunks to {output_path}")

def extract_book_number(filename):
    """
    Extract book number from cleaned filename.
    For example: 'cleaned_book-1.txt' -> 1
    
    Args:
        filename (str): The cleaned text filename
    
    Returns:
        int: Book number
    """
    # Remove 'cleaned_book-' prefix and '.txt' suffix
    try:
        book_num = filename.replace('cleaned_book-', '').replace('.txt', '')
        return int(book_num)
    except (ValueError, IndexError):
        return 1

def main():
    # List available cleaned text files
    available_files = list_available_cleaned_files(INPUT_FOLDER)
    
    if not available_files:
        print("No cleaned text files found in the input folder.")
        print(f"Expected location: {INPUT_FOLDER}")
        return
    
    # Loop until user presses 0
    while True:
        # Let user select a file
        selected_file = select_file(available_files)
        
        if selected_file:
            book_number = extract_book_number(selected_file)
            input_file_path = INPUT_FOLDER / selected_file
            
            # Load cleaned text
            print(f"\nLoading cleaned text from {selected_file}...")
            text = load_cleaned_text(input_file_path)
            
            if text is None:
                continue
            
            print(f"Loaded text with {len(text)} characters")
            
            # Chunk the text
            print("Chunking text with RecursiveCharacterTextSplitter...")
            chunks = chunk_text(text)
            
            print(f"Created {len(chunks)} chunks")
            
            # Create metadata for chunks
            print("Creating chunk metadata...")
            chunks_data = create_chunks_with_metadata(chunks)
            
            # Generate output file name with standardized naming
            output_filename = f"book-{book_number}_chunks.json"
            output_file_path = OUTPUT_FOLDER / output_filename
            
            # Save to JSON
            print("Saving chunks to JSON...")
            save_chunks_to_json(chunks_data, output_file_path)
            
            # Print statistics
            if chunks_data:
                print("\n=== Chunking Statistics ===")
                print(f"Total chunks: {len(chunks_data)}")
                print(f"Average chunk length: {sum(c['length'] for c in chunks_data) / len(chunks_data):.0f} characters")
                print(f"Average word count: {sum(c['word_count'] for c in chunks_data) / len(chunks_data):.0f} words")
                print(f"Min chunk length: {min(c['length'] for c in chunks_data)} characters")
                print(f"Max chunk length: {max(c['length'] for c in chunks_data)} characters")
            
            print()  # Add blank line for better readability
        else:
            # User pressed 0 or made invalid selection
            print("\nExiting text chunker. Goodbye!")
            break

if __name__ == "__main__":
    main()