from pathlib import Path

import cloudinary
import cloudinary.uploader

from app.config import settings


cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


def upload_file(file_path: str, folder: str = "autism-reports") -> str:
    response = cloudinary.uploader.upload(Path(file_path), folder=folder, resource_type="raw")
    return response["secure_url"]
