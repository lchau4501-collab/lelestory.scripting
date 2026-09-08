import re
import json
import logging
from typing import Dict, Any, Tuple
from pinyin_utils import validate_pinyin_syllables

logger = logging.getLogger("lelestory.scripting")

class Gatekeeper2:
    """Gatekeeper 2: Validates story script dialogue (ZH, Pinyin, EN), vocabulary, and image prompts."""

    def validate(self, combined_payload: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        batch_id = combined_payload.get("batch_id", 2)
        script = combined_payload.get("script", {})
        prompts = combined_payload.get("prompts", {})
        metadata = combined_payload.get("metadata", {})

        # 1. Script line check
        lines = script.get("lines", [])
        if not lines or len(lines) < 3:
            msg = f"GK2 FAIL: Script for batch #{batch_id} must have at least 3 story lines."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        for idx, line in enumerate(lines):
            zh = line.get("zh", "").strip()
            py = line.get("pinyin", "").strip()
            en = line.get("en", "").strip()
            if not zh or not py or not en:
                msg = f"GK2 FAIL: Line #{idx+1} in batch #{batch_id} is missing zh, pinyin, or English translation."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

        # 2. Vocabulary check
        vocab = script.get("vocabulary", [])
        if len(vocab) < 5:
            msg = f"GK2 FAIL: Must have at least 5 key vocabulary items in batch #{batch_id}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        # 3. Visual Prompts check
        tab1 = prompts.get("tab1_scenes", [])
        tab2 = prompts.get("tab2_elements", [])
        if not tab1 or not tab2:
            msg = f"GK2 FAIL: Missing Tab 1 scenes or Tab 2 elements prompts in batch #{batch_id}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        combined_payload["status"] = "GK2_Passed"
        logger.info(f"GK2 PASSED for story batch #{batch_id}")
        return True, "GK2 Passed", combined_payload

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gatekeeper 2 Validator")
    parser.add_argument("--idea", type=str, default="artifacts/idea_gk1.json")
    parser.add_argument("--output", type=str, default="artifacts/script_gk2.json")
    args = parser.parse_args()

    from script_generator import ScriptGenerator
    from prompt_builder import PromptBuilder
    from metadata_builder import MetadataBuilder

    with open(args.idea, "r", encoding="utf-8") as f:
        idea = json.load(f)

    sg = ScriptGenerator(idea)
    script_data = sg.generate_script()
    pb = PromptBuilder(script_data)
    prompts_data = pb.build_prompts()
    mb = MetadataBuilder(script_data)
    meta_data = mb.build_metadata()

    batch_num = idea.get("batch_id") or idea.get("row_id") or 2
    if int(batch_num) < 2:
        batch_num = 2

    combined = {
        "batch_id": int(batch_num),
        "row_id": int(batch_num),
        "title": idea.get("title", ""),
        "story_plot": idea.get("story_plot", ""),
        "gfolder_id": idea.get("gfolder_id", ""),
        "gfolder_url": idea.get("gfolder_url", ""),
        "script": script_data,
        "prompts": prompts_data,
        "metadata": meta_data,
        "status": "Pending_GK2"
    }

    gk2 = Gatekeeper2()
    passed, reason, updated = gk2.validate(combined)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    if not passed:
        exit(1)
