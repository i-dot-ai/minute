def get_file_s3_key(user_email: str, file_name: str, file_type: str = "multimedia") -> str:
    """
    Generate a consistent S3 file key for user uploads.

    Args:
        user_email (str): The email of the user uploading the file
        extension (str): The file extension

    Returns:
        str: The generated file key in the format 'user-uploads/{email}/{uuid}.{extension}'
    """
    if file_type == "document":
        return f"app_data/document-uploads/{user_email}/{file_name}"
    return f"app_data/user-uploads/{user_email}/{file_name}"
