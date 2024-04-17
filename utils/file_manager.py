import tempfile

def save_file_temporarily(file):
    # Create a temporary file within the system's temp directory
    # Note: NamedTemporaryFile is opened in 'w+b' mode by default
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name
        # Since we're using the file context manager, the file is already created
        # Now we just need to write the uploaded file content to it
        file.save(temp_file_path)
        print(f"Saving file temporarily to {temp_file_path}")
    # Return the path to the temp file
    # Note: The file is not automatically deleted, so you should handle cleanup after use
    return temp_file_path
