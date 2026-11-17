"""
Secure File Upload Utility
The Baseline Society
"""

import os
import uuid
from typing import Optional
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def is_allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_logo(file_storage: Optional[FileStorage], subfolder: str = "tournaments/logos") -> Optional[str]:
    """
    Validates and securely saves an uploaded logo image file.
    Returns the relative URL path (/static/uploads/...) or None if no valid file.
    """
    if not file_storage or not file_storage.filename or file_storage.filename.strip() == "":
        return None

    filename = file_storage.filename.strip()
    if not is_allowed_image(filename):
        raise ValueError("Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP, SVG.")

    # Generate sanitized and collision-free filename
    ext = filename.rsplit(".", 1)[1].lower()
    base_name = secure_filename(filename.rsplit(".", 1)[0])[:30]
    unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}.{ext}"

    # Determine base directory
    base_dir = os.path.join(current_app.root_path, "web", "static", "uploads", subfolder)
    os.makedirs(base_dir, exist_ok=True)

    file_path = os.path.join(base_dir, unique_name)
    file_storage.save(file_path)

    return f"/static/uploads/{subfolder}/{unique_name}"
