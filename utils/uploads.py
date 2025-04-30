from llmproxy import pdf_upload, text_upload

def handbook_upload(user_id):
    try:
        all_references = ["cs_handbook.pdf", "soe-grad-handbook.pdf", "filtered_grad_courses.pdf"]
        for reference in all_references:
            response = pdf_upload(
                path = f'resources/{reference}',
                session_id = 'cs-advising-handbooks-v5-' + user_id,
                strategy = 'smart'
            )
            print("✅ " + reference + " is successfully loaded")

    except Exception as e:
        print(f"❌ Error uploading handbooks: {str(e)}")

def get_txt(filename):
    """
    Reads a text file and returns its contents as a string.
    
    Args:
        filename (str): Path to the text file to be read
        
    Returns:
        str: The contents of the text file
        
    Raises:
        FileNotFoundError: If the file does not exist
        IOError: If there is an error reading the file
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The file '{filename}' was not found.")
    except IOError as e:
        raise IOError(f"Error reading file '{filename}': {e}")

def handbook_txt_upload(user_id):
    try:
        all_txts = ["cs-handbook.txt", "soe-handbook.txt", "courses.txt"]
        for txt in all_txts:
            response = text_upload(
                    text = get_txt(f"resources/{txt}"),
                    session_id = 'cs-advising-handbooks-v5-' + user_id,
                    strategy = 'fixed')
            print("✅ " + txt + " is successfully loaded")
    except Exception as e:
        print(f"❌ Error uploading handbooks: {str(e)}")
            