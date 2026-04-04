import PyPDF2
import os

# Define base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # retrieval-local folder
DATA_FOLDER = os.path.join(BASE_DIR, "data")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs", "pdf_to_text_output")

def list_available_pdfs(data_folder):
    """
    List all available PDF files in the data folder.
    
    Args:
        data_folder (str): Path to the data folder
    
    Returns:
        list: List of PDF filenames (without extension)
    """
    if not os.path.exists(data_folder):
        print(f"Error: Data folder not found at {data_folder}")
        return []
    
    pdf_files = [f for f in os.listdir(data_folder) if f.lower().endswith('.pdf')]
    return sorted(pdf_files)

def select_book(pdf_list):
    """
    Display available books and let user select one.
    
    Args:
        pdf_list (list): List of available PDF filenames
    
    Returns:
        str: Selected PDF filename or None if invalid selection
    """
    if not pdf_list:
        print("No PDF files found in the data folder.")
        return None
    
    print("\n" + "="*50)
    print("Available Books:")
    print("="*50)
    for idx, pdf_file in enumerate(pdf_list, 1):
        print(f"{idx}. {pdf_file}")
    
    print("\n" + "="*50)
    try:
        choice = int(input("Enter the book number to convert (or 0 to cancel): "))
        if choice == 0:
            print("Conversion cancelled.")
            return None
        if 1 <= choice <= len(pdf_list):
            return pdf_list[choice - 1]
        else:
            print("Invalid selection. Please enter a valid book number.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

def extract_pdf_to_text(pdf_path, output_folder, book_number):
    """
    Extract text content from a PDF file and save it to a text file.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_folder (str): Path to the output folder
        book_number (int): Book number for standardized naming
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Open and read the PDF
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_content = ""
            
            # Extract text from all pages
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text()
                text_content += "\n"
        
        # Generate output file name with standardized naming
        output_filename = f"book-{book_number}.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Save extracted text to file
        with open(output_path, 'w', encoding='utf-8') as text_file:
            text_file.write(text_content)
        
        print(f"\n✓ Text extracted successfully!")
        print(f"  PDF: {os.path.basename(pdf_path)}")
        print(f"  Output: {output_path}")
        return output_path
    
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
    except Exception as e:
        print(f"Error: {str(e)}")

# Usage
if __name__ == "__main__":
    # List available PDFs
    available_pdfs = list_available_pdfs(DATA_FOLDER)
    
    if not available_pdfs:
        print("No PDF files found in the data folder.")
        print(f"Expected location: {DATA_FOLDER}")
    else:
        # Loop until user presses 0
        while True:
            # Let user select a book
            selected_pdf = select_book(available_pdfs)
            
            if selected_pdf:
                book_number = available_pdfs.index(selected_pdf) + 1
                pdf_full_path = os.path.join(DATA_FOLDER, selected_pdf)
                extract_pdf_to_text(pdf_full_path, OUTPUT_FOLDER, book_number)
                print()  # Add blank line for better readability
            else:
                # User pressed 0 or made invalid selection
                if selected_pdf is None:
                    print("\nExiting PDF converter. Goodbye!")
                    break