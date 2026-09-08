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

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client() -> Optional[gspread.Client]:
    env_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON") or os.environ.get("SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            info = json.loads(env_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to load credentials from env JSON: {e}")
            return None

    local_path = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json")
    if os.path.exists(local_path):
        try:
            creds = Credentials.from_service_account_file(local_path, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to load credentials from file {local_path}: {e}")
            return None

    logger.warning("No Google Service Account credentials found.")
    return None

import urllib.request
import re

APPS_SCRIPT_WEBHOOK = os.environ.get(
    "DOCS_WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbzSn6Jv0fCltjFtm-_noIRJDUOz9BtViNFOmLsaLTSuZefu3Ij6O09mgBhFcnDcVjtP/exec"
)

def create_gdoc_via_webhook(folder_id: str, title: str, content: str) -> Optional[str]:
    """Calls Google Apps Script Webhook to create native Google Doc in project folder."""
    if not APPS_SCRIPT_WEBHOOK:
        return None
    try:
        payload = {
            "folderId": folder_id,
            "title": f"Script - 《{title}》",
            "content": content
        }
        req = urllib.request.Request(
            APPS_SCRIPT_WEBHOOK,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                doc_url = data.get("url") or f"https://docs.google.com/document/d/{data.get('id')}/edit"
                logger.info(f"✅ Created GDoc via Webhook: {doc_url}")
                return doc_url
            else:
                logger.error(f"❌ Webhook error creating GDoc: {data.get('error')}")
    except Exception as e:
        logger.error(f"❌ Failed to call Google Docs Webhook: {e}")
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
        row_idx = max(int(row_id), 2)  # Invariance: Row Index == Batch ID (#), >= 2
        
        title = data.get("title", "")
        script = data.get("script", {})
        lines = script.get("lines", [])
        vocab = script.get("vocabulary", [])
        outro = script.get("outro", {})
        prompts = data.get("prompts", {})
        metadata = data.get("metadata", {})

        # 1. Format Script: 4 Scenes + Vocabulary + Outro (ZH + Pinyin + Natural English)
        script_blocks = [f"【故事剧本 / STORY SCRIPT: 《{title}》】\n"]
        for idx, line in enumerate(lines, 1):
            s_num = line.get("scene_num", idx)
            spk = line.get("speaker", "Narrator")
            zh = line.get("zh", "")
            py = line.get("pinyin", "")
            en = line.get("en", "")
            script_blocks.append(
                f"[Scene {s_num} - {spk}]\n"
                f"ZH: {zh}\n"
                f"PY: {py}\n"
                f"EN: {en}\n"
            )

        if vocab:
            script_blocks.append("【重点词汇 / KEY VOCABULARY】")
            for v_idx, v in enumerate(vocab, 1):
                script_blocks.append(f"{v_idx}. {v.get('word')} ({v.get('pinyin')}): {v.get('en')}")
            script_blocks.append("")

        if outro:
            script_blocks.append("【循环结尾 / OUTRO LOOP】")
            script_blocks.append(f"ZH: {outro.get('zh')}")
            script_blocks.append(f"PY: {outro.get('pinyin')}")
            script_blocks.append(f"EN: {outro.get('en')}\n")

        full_script_text = "\n".join(script_blocks)

        # 2. Extract Folder ID from Col 5 (GFolder)
        gfolder_url = ws.cell(row_idx, 5).value or ""
        folder_id = ""
        if "folders/" in gfolder_url:
            folder_id = gfolder_url.split("folders/")[1].split("?")[0].strip()
        elif "id=" in gfolder_url:
            folder_id = gfolder_url.split("id=")[1].split("&")[0].strip()

        # 3. Create Google Doc for Script in Folder via Webhook and obtain GDoc URL for Col F
        doc_url = create_gdoc_via_webhook(folder_id, f"Script - 《{title}》", full_script_text)
        script_cell_value = doc_url if doc_url else full_script_text

        # 4. Format Image Prompts and Create GDoc "Image prompt" in Folder via Webhook for Col H
        prompt_text = prompts.get("formatted_gdoc_text", "")
        prompt_doc_url = None
        if prompt_text:
            prompt_doc_url = create_gdoc_via_webhook(folder_id, "Image prompt", prompt_text)
        prompt_cell_value = prompt_doc_url if prompt_doc_url else prompt_text

        # 5. Format Metadata (YouTube, TikTok, Facebook with required hashtags)
        meta_text = metadata.get("formatted_metadata_txt", "")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Invariance: Row Index == Batch ID (#)
        # Col 1: #
        # Col 4: Status -> "Script" (as specified in storydraft)
        # Col 6: Script (F) -> GDoc URL strictly
        # Col 8: Image Prompt (H) -> Image Prompt GDoc URL strictly
        # Col 11: metadata (K) -> meta_text
        # Col 17: Notes (Q)
        ws.update_cell(row_idx, 1, str(row_idx))
        ws.update_cell(row_idx, 4, "Script")
        ws.update_cell(row_idx, 6, script_cell_value)
        if prompt_cell_value:
            ws.update_cell(row_idx, 8, prompt_cell_value)
        if meta_text:
            ws.update_cell(row_idx, 11, meta_text)
        ws.update_cell(row_idx, 17, f"GK2 Passed - Story & Image Prompts in GDoc with English Translation on {timestamp}")

        logger.info(f"🎉 Successfully synced Row #{row_idx} to GSheet tab '{TAB_NAME}': Status='Script', Script GDoc={doc_url}, ImagePrompt GDoc={prompt_doc_url}")
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
