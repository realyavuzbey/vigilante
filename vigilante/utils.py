import os
import stem
import json
import stem.control
from datetime import datetime
from .config import ua

def rotate_user_agent():
    """
    Returns a random user-agent string.
    If fake-useragent fails, falls back to a default UA.
    """
    try:
        return ua.random if ua else _fallback_ua()
    except Exception:
        return _fallback_ua()

def _fallback_ua():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    
def export_json(data, class_name="Result", output_dir=None):
    """
    Exports JSON data to a timestamped file inside a 'results' folder in the current working directory.
    Filename format: ClassName_YYYYMMDD_HHMMSS.json
    """
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "results")
    
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{class_name}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
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
