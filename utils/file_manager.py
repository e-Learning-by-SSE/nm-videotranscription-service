import tempfile

def save_file_temporarily(file):
    # Create a temporary file within the system's temp directory
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name
        file.save(temp_file_path)
        print(f"Saving file temporarily to {temp_file_path}")
    return temp_file_path
