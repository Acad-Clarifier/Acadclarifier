import os
import re

# Define base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # retrieval-local folder
INPUT_FOLDER = os.path.join(BASE_DIR, "outputs", "pdf_to_text_output")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs", "cleaned_text_output")

def list_available_text_files(input_folder):
    """
    List all available text files in the input folder.
    
    Args:
        input_folder (str): Path to the folder containing text files
    
    Returns:
        list: List of text filenames (sorted)
    """
    if not os.path.exists(input_folder):
        print(f"Error: Input folder not found at {input_folder}")
        return []
    
    text_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.txt')]
    return sorted(text_files)

def select_file(file_list):
    """
    Display available text files and let user select one.
    
    Args:
        file_list (list): List of available text filenames
    
    Returns:
        str: Selected text filename or None if invalid selection
    """
    if not file_list:
        print("No text files found in the input folder.")
        return None
    
    print("\n" + "="*50)
    print("Available Text Files:")
    print("="*50)
    for idx, text_file in enumerate(file_list, 1):
        print(f"{idx}. {text_file}")
    
    print("\n" + "="*50)
    try:
        choice = int(input("Enter the file number to clean (or 0 to cancel): "))
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

def clean_text(text_content):
    """
    Clean text by removing unwanted characters and normalizing whitespace.
    
    Args:
        text_content (str): Raw text content
    
    Returns:
        str: Cleaned text content
    """
    # Remove extra whitespace (multiple spaces, tabs, etc.)
    text_content = re.sub(r'[ \t]+', ' ', text_content)
    
    # Remove multiple newlines and replace with single newline
    text_content = re.sub(r'\n\s*\n', '\n', text_content)
    
    # Remove leading and trailing whitespace from each line
    lines = text_content.split('\n')
    lines = [line.strip() for line in lines]
    text_content = '\n'.join(lines)
    
    # Remove extra spaces around punctuation
    text_content = re.sub(r'\s+([.,!?;:])', r'\1', text_content)
    
    # Remove special characters that are likely extraction artifacts
    # Keep alphanumeric, common punctuation, and whitespace
    text_content = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text_content)
    
    # Strip leading and trailing whitespace from entire document
    text_content = text_content.strip()
    
    return text_content

def process_text_file(input_path, output_folder, file_number):
    """
    Read, clean, and save text file.
    
    Args:
        input_path (str): Path to the input text file
        output_folder (str): Path to the output folder
        file_number (int): File number for standardized naming
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Read the input file
        with open(input_path, 'r', encoding='utf-8') as input_file:
            text_content = input_file.read()
        
        # Get original content length
        original_length = len(text_content)
        
        # Clean the text
        cleaned_content = clean_text(text_content)
        
        # Get cleaned content length
        cleaned_length = len(cleaned_content)
        
        # Generate output file name with standardized naming
        output_filename = f"cleaned_book-{file_number}.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Save cleaned text to file
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(cleaned_content)
        
        print(f"\n✓ Text cleaned successfully!")
        print(f"  Input: {os.path.basename(input_path)}")
        print(f"  Output: {output_filename}")
        print(f"  Original size: {original_length} characters")
        print(f"  Cleaned size: {cleaned_length} characters")
        print(f"  Reduction: {original_length - cleaned_length} characters removed")
        return output_path
    
    except FileNotFoundError:
        print(f"Error: Text file not found at {input_path}")
    except Exception as e:
        print(f"Error: {str(e)}")

# Usage
if __name__ == "__main__":
    # List available text files
    available_files = list_available_text_files(INPUT_FOLDER)
    
    if not available_files:
        print("No text files found in the input folder.")
        print(f"Expected location: {INPUT_FOLDER}")
    else:
        # Loop until user presses 0
        while True:
            # Let user select a file
            selected_file = select_file(available_files)
            
            if selected_file:
                file_number = available_files.index(selected_file) + 1
                input_full_path = os.path.join(INPUT_FOLDER, selected_file)
                process_text_file(input_full_path, OUTPUT_FOLDER, file_number)
                print()  # Add blank line for better readability
            else:
                # User pressed 0 or made invalid selection
                print("\nExiting text cleaner. Goodbye!")
                break
