def get_file_s3_key(user_email: str, file_name: str) -> str:
    """
    Generate a consistent S3 file key for user uploads.

    Args:
        user_email (str): The email of the user uploading the file
        file_name (str): the name of the file to be uploaded

    Returns:
        str: The generated file key in the format 'user-uploads/{email}/{file_name}'
    """
    return f"restricted/user-uploads/{user_email}/{file_name}"
