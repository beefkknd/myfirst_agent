"""
File and directory operation utilities
"""

import os
import re
import shutil
import urllib.parse
from typing import Optional
from pathlib import Path


def ensure_directory(directory_path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to directory to create
        
    Returns:
        Absolute path to the directory
    """
    abs_path = os.path.abspath(directory_path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Args:
        filename: Raw filename string
        max_length: Maximum allowed filename length
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove or replace invalid characters
    # Keep only alphanumeric, hyphens, underscores, and dots
    safe_filename = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', filename)
    
    # Remove multiple consecutive underscores
    safe_filename = re.sub(r'_{2,}', '_', safe_filename)
    
    # Remove leading/trailing underscores and dots
    safe_filename = safe_filename.strip('_.')
    
    # Limit length
    if len(safe_filename) > max_length:
        safe_filename = safe_filename[:max_length]
    
    # Ensure we have a valid filename
    if not safe_filename:
        safe_filename = "untitled"
    
    return safe_filename


def sanitize_url_for_filename(url: str, max_length: int = 100) -> str:
    """
    Convert URL to safe filename by extracting domain and path.
    
    Args:
        url: URL to convert
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename based on URL
    """
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.strip("/")
        
        # Create base filename from domain and path
        if path:
            filename_base = f"{domain}_{path}"
        else:
            filename_base = domain
        
        return sanitize_filename(filename_base, max_length)
        
    except Exception:
        # Fallback to hash-based filename
        return f"page_{hash(url) % 10000}"


def safe_move_file(source_path: str, destination_path: str) -> bool:
    """
    Safely move a file from source to destination with error handling.
    
    Args:
        source_path: Source file path
        destination_path: Destination file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(source_path):
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination_path)
            ensure_directory(dest_dir)
            
            shutil.move(source_path, destination_path)
            return True
    except Exception as e:
        print(f"⚠️ Failed to move file {source_path} -> {destination_path}: {e}")
    
    return False


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB, or 0 if file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)  # Convert to MB
    except Exception:
        pass
    
    return 0.0


def create_vessel_directory(base_dir: str, vessel_mmsi: str) -> str:
    """
    Create a vessel-specific directory structure.
    
    Args:
        base_dir: Base directory (e.g., "reports/search_results")
        vessel_mmsi: MMSI identifier for the vessel
        
    Returns:
        Path to vessel-specific directory
    """
    vessel_dir = os.path.join(base_dir, vessel_mmsi)
    return ensure_directory(vessel_dir)