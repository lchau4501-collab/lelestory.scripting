import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Tuple
import urllib.request
import re
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger("lelestory.gsheet")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0")
TAB_NAME = "story"
TARGET_ROW_HEIGHT_PX = 21

# Canonical Direct View URL Pattern for Google Drive files (Video Col L, HTML Col J)
DIRECT_VIEW_REGEX = re.compile(r"^https://drive\.google\.com/file/d/[a-zA-Z0-9_-]+/view\Z")
DRIVE_FILE_VIEW_REGEX = DIRECT_VIEW_REGEX

import importlib.util
from pathlib import Path

# Standard Column Mapping on tab 'story'
COL_MAP = {
    "id": "A",
    "title": "B",
    "plot": "C",
    "status": "D",
    "gfolder": "E",
    "script": "F",
    "voice": "G",
    "prompt": "H",
    "image": "I",
    "html": "J",
    "metadata": "K",
    "video": "L",
    "created_at": "P",
    "notes": "Q"
}

_gha_sync_path = Path(__file__).resolve().parent.parent.parent / "deploy" / "gha_public_workflows" / "scripts" / "gsheet_sync.py"
if _gha_sync_path.exists():
    try:
        _spec = importlib.util.spec_from_file_location("_gha_gsheet_sync", str(_gha_sync_path))
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            build_enforce_row_height_request = getattr(_mod, "build_enforce_row_height_request", None)
            enforce_21px_row_height = getattr(_mod, "enforce_21px_row_height", None)
            update_story_row = getattr(_mod, "update_story_row", None)
            verify_sheet_invariants = getattr(_mod, "verify_sheet_invariants", None)
            get_service_account_credentials = getattr(_mod, "get_service_account_credentials", None)
            execute_with_retry = getattr(_mod, "execute_with_retry", None)
            COL_MAP = getattr(_mod, "COL_MAP", COL_MAP)
    except Exception:
        pass

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials() -> Optional[Credentials]:
    env_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON") or os.environ.get("SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            info = json.loads(env_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to load credentials from env JSON: {e}")
            return None

    local_path = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json")
    if os.path.exists(local_path):
        try:
            return Credentials.from_service_account_file(local_path, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to load credentials from file {local_path}: {e}")
            return None

    logger.warning("No Google Service Account credentials found.")
    return None

def get_gspread_client() -> Optional[gspread.Client]:
    creds = get_credentials()
    if creds:
        try:
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to authorize gspread client: {e}")
            return None
    return None

import requests

APPS_SCRIPT_WEBHOOK = os.environ.get(
    "DOCS_WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbzSn6Jv0fCltjFtm-_noIRJDUOz9BtViNFOmLsaLTSuZefu3Ij6O09mgBhFcnDcVjtP/exec"
)

def create_gdoc_via_webhook(folder_id: str, title: str, content: str) -> Optional[str]:
    """
    Calls Google Apps Script Webhook to create native Google Doc in project folder.
    Uses title exactly as provided (e.g. 'Script - 《Title》' or 'Image prompt').
    """
    if not APPS_SCRIPT_WEBHOOK:
        return None
    try:
        payload = {
            "folderId": folder_id,
            "title": title,  # Passed title used directly, not hardcoded
            "content": content
        }
        resp = requests.post(APPS_SCRIPT_WEBHOOK, json=payload, timeout=60, allow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                doc_url = data.get("url") or f"https://docs.google.com/document/d/{data.get('id')}/edit"
                logger.info(f"✅ Created GDoc via Webhook: {doc_url} ('{title}')")
                return doc_url
            else:
                logger.error(f"❌ Webhook error creating GDoc '{title}': {data.get('error')}")
        else:
            logger.error(f"❌ Webhook returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"❌ Failed to call Google Docs Webhook: {e}")
    return None

def enforce_tab_story_row_height_21px(creds: Credentials, spreadsheet_id: str = SPREADSHEET_ID) -> bool:
    """Enforces strict 21px row height invariant on tab 'story' via Google Sheets API v4 updateDimensionProperties."""
    try:
        service = build("sheets", "v4", credentials=creds)
        ss = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = None
        row_count = 100
        for s in ss.get("sheets", []):
            if s["properties"]["title"] == TAB_NAME:
                sheet_id = s["properties"]["sheetId"]
                row_count = s["properties"]["gridProperties"]["rowCount"]
                break

        if sheet_id is None:
            logger.warning(f"Tab '{TAB_NAME}' not found in spreadsheet.")
            return False

        req = {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": row_count
                },
                "properties": {
                    "pixelSize": TARGET_ROW_HEIGHT_PX
                },
                "fields": "pixelSize"
            }
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [req]}).execute()
        logger.info(f"✅ Enforced strict {TARGET_ROW_HEIGHT_PX}px row height on tab '{TAB_NAME}' across {row_count} rows.")
        return True
    except Exception as e:
        logger.error(f"Failed to enforce 21px row height on tab '{TAB_NAME}': {e}")
        return False

def create_google_doc(folder_id: str, title: str, content: str) -> Optional[str]:
    """Creates Google Doc in folder via User OAuth API or Apps Script Webhook."""
    # Try User OAuth API first if available locally
    oauth_path = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json")
    if os.path.exists(oauth_path):
        try:
            from google.oauth2.credentials import Credentials as UserOAuthCreds
            from google.auth.transport.requests import Request as AuthRequest
            with open(oauth_path, "r", encoding="utf-8") as f:
                tdata = json.load(f)
            ucreds = UserOAuthCreds.from_authorized_user_info(tdata)
            if ucreds.expired and ucreds.refresh_token:
                ucreds.refresh(AuthRequest())
                with open(oauth_path, "w", encoding="utf-8") as f:
                    f.write(ucreds.to_json())
            docs_svc = build("docs", "v1", credentials=ucreds)
            drive_svc = build("drive", "v3", credentials=ucreds)
            doc = docs_svc.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")
            if content and content.strip():
                docs_svc.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": [{"insertText": {"location": {"index": 1}, "text": content.replace("\x00", "")}}]}
                ).execute()
            if folder_id:
                drive_svc.files().update(fileId=doc_id, addParents=folder_id, fields="id, parents").execute()
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            logger.info(f"✅ Created GDoc via User OAuth: {doc_url} ('{title}')")
            return doc_url
        except Exception as e:
            logger.warning(f"Failed to create GDoc via User OAuth ({e}), trying Webhook...")

    # Fallback to Apps Script Webhook
    return create_gdoc_via_webhook(folder_id, title, content)

def sync_scripting_to_sheet(script_path: str, target_row: int = 2):
    if not os.path.exists(script_path):
        logger.error(f"Script file not found: {script_path}")
        return False

    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    creds = get_credentials()
    if not creds:
        logger.warning("⚠️ Skipping GSheet sync: Credentials not available.")
        return False

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

        # 1. Format Script: 8–10 Scenes + Vocabulary + Outro (ZH + Pinyin + Natural English)
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

        # 3. Create Google Doc for Script in Folder and obtain GDoc URL for Col F
        doc_url = create_google_doc(folder_id, f"Script - 《{title}》", full_script_text)
        script_cell_value = doc_url if doc_url else full_script_text

        # 4. Format Image Prompts and Create GDoc "Prompt - 《{title}》" in Folder for Col H
        prompt_text = prompts.get("formatted_gdoc_text", "")
        prompt_doc_url = None
        if prompt_text:
            prompt_doc_url = create_google_doc(folder_id, f"Prompt - 《{title}》", prompt_text)
        prompt_cell_value = prompt_doc_url if prompt_doc_url else prompt_text

        # 5. Format Metadata and Create GDoc "Metadata - 《{title}》" in Folder for Col K
        meta_text = metadata.get("formatted_metadata_txt", "")
        meta_doc_url = None
        if meta_text:
            meta_doc_url = create_google_doc(folder_id, f"Metadata - 《{title}》", meta_text)
        meta_cell_value = meta_doc_url if meta_doc_url else meta_text

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Invariance: Row Index == Batch ID (#)
        # Batch update cells to eliminate 429 quota exhaustion:
        batch_updates = [
            {"range": f"A{row_idx}", "values": [[str(row_idx)]]},
            {"range": f"D{row_idx}", "values": [["Script"]]},
            {"range": f"F{row_idx}", "values": [[script_cell_value]]}
        ]
        if prompt_cell_value:
            batch_updates.append({"range": f"H{row_idx}", "values": [[prompt_cell_value]]})
        if meta_cell_value:
            batch_updates.append({"range": f"K{row_idx}", "values": [[meta_cell_value]]})
        batch_updates.append({
            "range": f"Q{row_idx}",
            "values": [[f"GK2 Passed - Story, Image Prompts & Metadata in GDoc with English on {timestamp}"]]
        })

        ws.batch_update(batch_updates)

        # Enforce strict 21px row height invariant
        enforce_tab_story_row_height_21px(creds, SPREADSHEET_ID)

        logger.info(f"🎉 Successfully synced Row #{row_idx} to GSheet tab '{TAB_NAME}' in 1 batch: Status='Script', Script GDoc={doc_url}, ImagePrompt GDoc={prompt_doc_url}, Metadata GDoc={meta_doc_url}")
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
