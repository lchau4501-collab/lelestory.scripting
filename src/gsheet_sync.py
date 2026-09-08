import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger("lelestory.gsheet")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0")
TAB_NAME = "story"

def get_gspread_client() -> Optional[gspread.Client]:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    env_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON") or os.environ.get("SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            info = json.loads(env_json)
            creds = Credentials.from_service_account_info(info, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to load credentials from env JSON: {e}")
            return None

    # Fallback to local profile
    local_path = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json")
    if os.path.exists(local_path):
        try:
            creds = Credentials.from_service_account_file(local_path, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to load credentials from file {local_path}: {e}")
            return None

    logger.warning("No Google Service Account credentials found.")
    return None

def sync_scripting_to_sheet(script_path: str, target_row: int = 2):
    if not os.path.exists(script_path):
        logger.error(f"Script file not found: {script_path}")
        return False

    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    client = get_gspread_client()
    if not client:
        logger.warning("⚠️ Skipping GSheet sync: GSpread client not available.")
        return False

    try:
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = ss.worksheet(TAB_NAME)

        row_id = data.get("batch_id") or data.get("row_id") or target_row
        row_idx = max(int(row_id), 2)
        
        script = data.get("script", {})
        lines = script.get("lines", [])
        prompts = data.get("prompts", {})
        metadata = data.get("metadata", {})

        # Format script lines
        formatted_script = []
        for idx, line in enumerate(lines, 1):
            spk = line.get("speaker", "Narrator")
            zh = line.get("zh", "")
            py = line.get("pinyin", "")
            vi = line.get("vi", "")
            formatted_script.append(f"[Phân cảnh {idx} - {spk}]\nZH: {zh}\nPY: {py}\nVI: {vi}")
        script_text = "\n\n".join(formatted_script)

        # Format prompts
        ig_prompts = prompts.get("instagram_carousel", [])
        prompt_text = "\n---\n".join(ig_prompts) if ig_prompts else ""

        # Format metadata
        meta_json_str = json.dumps(metadata, ensure_ascii=False)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Invariance: Row Index == Batch ID (#)
        # Column 1: #
        # Column 4: Status (D) -> GK2_Passed
        # Column 6: Script (F)
        # Column 8: Image Prompt (H)
        # Column 11: metadata (K)
        # Column 17: Notes (Q)
        ws.update_cell(row_idx, 1, str(row_idx))
        ws.update_cell(row_idx, 4, "GK2_Passed")
        ws.update_cell(row_idx, 6, script_text)
        if prompt_text:
            ws.update_cell(row_idx, 8, prompt_text)
        if meta_json_str:
            ws.update_cell(row_idx, 11, meta_json_str)
        ws.update_cell(row_idx, 17, f"GK2 Scripted & Validated via Live AI on {timestamp}")

        logger.info(f"🎉 Successfully synced Row #{row_idx} to GSheet tab '{TAB_NAME}': Status='GK2_Passed', Total Lines={len(lines)}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to sync scripting to GSheet: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=str, default="artifacts/script_gk2.json")
    parser.add_argument("--row-id", type=int, default=2)
    args = parser.parse_args()

    sync_scripting_to_sheet(args.script, args.row_id)
