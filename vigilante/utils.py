import os
import csv
import time
import docx
import stem
import json
import PyPDF2
import random
import exifread
from PIL import Image
import stem.control
from datetime import datetime
from urllib.parse import urlparse
from .config import BLACKLISTED_UAS, FAKE_UAS
from pymediainfo import MediaInfo

def basedir(name="results"):
    """
    Returns the absolute path of a base directory under the current working directory.
    Creates the directory if it does not exist.

    Args:
        name (str): Folder name (e.g., 'downloads', 'results', 'logs').

    Returns:
        str: Absolute path to the created/verified base directory.
    """
    base_dir = os.path.join(os.getcwd(), name)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def rotate_ua():
    """
    Returns a random user-agent from FAKE_UAS, avoiding blacklisted ones.
    """
    while True:
        agent = random.choice(FAKE_UAS)
        if not any(bad.lower() in agent.lower() for bad in BLACKLISTED_UAS):
            return agent

def _fallback_ua():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    
def log(message, level="INFO", debug=False, log_file="vigilante.log"):
    """
    Global logging utility for all modules.
    
    Args:
        message (str): Message to log.
        level (str): Log level (e.g., INFO, ERROR).
        debug (bool): If True, prints to stdout.
        log_file (str): File to append logs to.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{level}] {timestamp} - {message}"

    if debug:
        print(log_line)

    try:
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        full_path = os.path.join(logs_dir, log_file)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        if debug:
            print(f"[LoggerError] Failed to write log: {e}")
    
def export_data(data, export_as="json", class_name="Result", output_dir=None):
    """
    Exports data in json, csv, txt, or markdown format.
    """
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{class_name}_{timestamp}.{export_as}"
    filepath = os.path.join(output_dir, filename)

    try:
        if export_as == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        elif export_as == "csv":
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["engine", "title", "url", "description", "domain"])
                for engine, entries in data.items():
                    for entry in entries:
                        writer.writerow([
                            engine,
                            entry.get("title", ""),
                            entry.get("url", ""),
                            entry.get("description", ""),
                            entry.get("domain", "")
                        ])

        elif export_as == "markdown":
            with open(filepath, "w", encoding="utf-8") as f:
                for engine, entries in data.items():
                    f.write(f"## {engine}\n\n")
                    for entry in entries:
                        f.write(f"**{entry.get('title', 'No Title')}**  \n")
                        f.write(f"{entry.get('description', '')}  \n")
                        f.write(f"[Link]({entry.get('url', '')}) — `{entry.get('domain', '')}`\n\n")

        elif export_as == "txt":
            with open(filepath, "w", encoding="utf-8") as f:
                for engine, entries in data.items():
                    f.write(f"=== {engine} ===\n")
                    for entry in entries:
                        f.write(f"{entry.get('title', 'No Title')}\n")
                        f.write(f"{entry.get('description', '')}\n")
                        f.write(f"{entry.get('url', '')} ({entry.get('domain', '')})\n")
                        f.write("\n")
        else:
            return f"[Export Error] Unknown format: {export_as}"

        return filepath

    except Exception as e:
        return f"[Export Error] {e}"
    
def rotate_ip():
    try:
        with stem.control.Controller.from_port(port=9051) as c:
            c.authenticate()
            c.signal(stem.Signal.NEWNYM)
            return True
    except Exception as e:
        return {"error": str(e)}


def parse_exif(path):
    """
    Extract EXIF metadata from an image file using exifread.
    
    Args:
        path (str): The image file path.
        
    Returns:
        dict: Extracted EXIF metadata.
    """
    metadata = {}
    try:
        with open(path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            for tag in tags:
                metadata[tag] = str(tags[tag])
    except Exception as e:
        metadata["error"] = str(e)
    return metadata


def parse_pdf(path):
    """
    Extract metadata from a PDF file using PyPDF2.
    
    Args:
        path (str): The PDF file path.
        
    Returns:
        dict: Extracted PDF metadata.
    """
    metadata = {}
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            info = reader.metadata
            if info:
                for key, value in info.items():
                    metadata[key] = str(value)
    except Exception as e:
        metadata["error"] = str(e)
    return metadata


def parse_docx(path):
    """
    Extract metadata from a DOCX file using python-docx.
    
    Args:
        path (str): The DOCX file path.
        
    Returns:
        dict: Extracted DOCX metadata.
    """
    metadata = {}
    try:
        doc = docx.Document(path)
        core_properties = doc.core_properties
        metadata["author"] = core_properties.author
        metadata["title"] = core_properties.title
        metadata["subject"] = core_properties.subject
        metadata["created"] = str(core_properties.created)
        metadata["modified"] = str(core_properties.modified)
    except Exception as e:
        metadata["error"] = str(e)
    return metadata


def parse_media(path):
    """
    Extract metadata from a media (video) file using pymediainfo if available.
    
    Args:
        path (str): The media file path.
        
    Returns:
        dict: Extracted media metadata.
    """
    metadata = {}
    if MediaInfo is None:
        metadata["warning"] = "pymediainfo is not installed."
        return metadata
    try:
        media_info = MediaInfo.parse(path)
        for track in media_info.tracks:
            if track.track_type == "General":
                metadata.update({
                    "duration": track.duration,
                    "file_size": track.file_size,
                    "format": track.format,
                    "title": track.title,
                    "album": track.album,
                    "performer": track.performer,
                })
            elif track.track_type == "Video":
                metadata.update({
                    "width": track.width,
                    "height": track.height,
                    "frame_rate": track.frame_rate,
                    "bit_rate": track.bit_rate,
                    "codec": track.codec,
                })
    except Exception as e:
        metadata["error"] = str(e)
    return metadata
