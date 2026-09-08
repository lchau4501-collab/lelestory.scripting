import re
import json
import logging
from typing import Dict, Any, Tuple
from pinyin_utils import validate_pinyin_syllables

logger = logging.getLogger("lelestory.scripting")

class Gatekeeper2:
    """Gatekeeper 2: Validates script dialogue, pinyin formatting, visual prompts, and metadata integrity."""

    def validate(self, combined_payload: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        batch_id = combined_payload.get("batch_id", 0)
        script = combined_payload.get("script", {})
        prompts = combined_payload.get("prompts", {})
        metadata = combined_payload.get("metadata", {})

        # 1. Script line check
        lines = script.get("lines", [])
        if not lines or len(lines) < 2:
            msg = f"GK2 FAIL: Script for batch #{batch_id} must have at least 2 lines."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        for idx, line in enumerate(lines):
            zh = line.get("zh", "")
            py = line.get("pinyin", "")
            vi = line.get("vi", "")
            if not zh or not py or not vi:
                msg = f"GK2 FAIL: Line #{idx+1} in batch #{batch_id} is missing zh, pinyin, or vi."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

        # 2. Prompt prefix format check
        prefix_pattern = re.compile(r"^\[(PIN|IG|FB|CARD|COMIC)-POST\d{3}-[A-Z0-9]+-\d+x\d+-ST\d\]")
        ig_prompts = prompts.get("instagram_carousel", [])
        if not ig_prompts:
            msg = f"GK2 FAIL: Missing instagram_carousel prompts in batch #{batch_id}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        for prompt_str in ig_prompts:
            if not prefix_pattern.match(prompt_str):
                msg = f"GK2 FAIL: Invalid prompt prefix format in '{prompt_str[:30]}...'."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

        # 3. Metadata check
        if not metadata.get("title") or not metadata.get("description"):
            msg = f"GK2 FAIL: Missing metadata title or description for batch #{batch_id}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        combined_payload["status"] = "GK2_Passed"
        logger.info(f"GK2 PASSED for batch #{batch_id}")
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
        "theme": idea.get("theme", "HANZIDEGUSHI"),
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
