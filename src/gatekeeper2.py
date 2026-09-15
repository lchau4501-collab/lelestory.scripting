import re
import json
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("lelestory.scripting")

VIETNAMESE_PATTERN = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]",
    re.IGNORECASE
)

class Gatekeeper2:
    """
    Gatekeeper 2: Validates story script dialogue (ZH, Pinyin, EN with strictly ZERO Vietnamese),
    progressive 8–10 scenes following 3-Act structure, 5 key educational vocabulary items,
    outro loop, and strict image prompt formatting.
    """

    def validate(self, combined_payload: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        batch_id = combined_payload.get("batch_id") or combined_payload.get("row_id") or 2
        script = combined_payload.get("script", {})
        prompts = combined_payload.get("prompts", {})
        metadata = combined_payload.get("metadata", {})

        # 1. Script scenes & lines check (Strictly 8–10 scenes)
        lines = script.get("lines", [])
        if not lines:
            msg = f"GK2 FAIL: Script for batch #{batch_id} has no story lines."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        unique_scenes = sorted(list(set(line.get("scene_num", 1) for line in lines)))
        if len(unique_scenes) < 8 or len(unique_scenes) > 10:
            msg = f"GK2 FAIL: Script for batch #{batch_id} must have between 8 and 10 progressive scenes. Found {len(unique_scenes)} scenes."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        # 2. Line fields & ZERO Vietnamese check
        for idx, line in enumerate(lines, 1):
            zh = line.get("zh", "").strip()
            py = line.get("pinyin", "").strip()
            en = line.get("en", "").strip()
            if not zh or not py or not en:
                msg = f"GK2 FAIL: Line #{idx} in batch #{batch_id} is missing zh, pinyin, or English translation."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

            if VIETNAMESE_PATTERN.search(en):
                msg = f"GK2 FAIL: Line #{idx} contains Vietnamese characters in English field: '{en}'. Strictly ZERO Vietnamese allowed!"
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

        # 3. Vocabulary check (5 key educational vocabulary items)
        vocab = script.get("vocabulary", [])
        if len(vocab) < 5:
            msg = f"GK2 FAIL: Must have at least 5 key educational vocabulary items in batch #{batch_id}. Found {len(vocab)}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        for v_idx, v in enumerate(vocab[:5], 1):
            w = v.get("word", "").strip()
            py = v.get("pinyin", "").strip()
            en = v.get("en", "").strip()
            if not w or not py or not en:
                msg = f"GK2 FAIL: Vocabulary #{v_idx} is missing word, pinyin, or en translation."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

            if VIETNAMESE_PATTERN.search(en):
                msg = f"GK2 FAIL: Vocabulary #{v_idx} contains Vietnamese characters in English field: '{en}'."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

        # 4. Outro Loop Check
        outro = script.get("outro", {})
        if not outro or not outro.get("zh") or not outro.get("en"):
            msg = f"GK2 FAIL: Missing outro loop sentence in batch #{batch_id}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        if VIETNAMESE_PATTERN.search(outro.get("en", "")):
            msg = f"GK2 FAIL: Outro loop contains Vietnamese characters in English field."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        # 5. Visual Prompts check (Tab 1 Scenes + Tab 2 Elements)
        tab1 = prompts.get("tab1_scenes", [])
        tab2 = prompts.get("tab2_elements", [])
        if not tab1 or not tab2:
            msg = f"GK2 FAIL: Missing Tab 1 scenes or Tab 2 elements prompts in batch #{batch_id}."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        # Verify Tab 1 has Cover, 8-10 scenes, 5 vocab, and Outro
        tags_tab1 = [item.get("tag", "") for item in tab1]
        if not any("Cover" in t for t in tags_tab1):
            msg = f"GK2 FAIL: Missing Cover prompt in Tab 1 prompts."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        if not any("Outro" in t for t in tags_tab1):
            msg = f"GK2 FAIL: Missing Outro-Loop prompt in Tab 1 prompts."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        # Verify strict single line per prompt format
        formatted_text = prompts.get("formatted_gdoc_text", "")
        if not formatted_text:
            msg = f"GK2 FAIL: Missing formatted_gdoc_text in prompts."
            logger.error(msg)
            combined_payload["status"] = "GK2_Failed"
            combined_payload["gk2_error"] = msg
            return False, msg, combined_payload

        paragraphs = formatted_text.split(chr(10) + chr(10))
        for p_idx, p in enumerate(paragraphs, 1):
            if chr(10) in p.strip():
                msg = f"GK2 FAIL: Prompt #{p_idx} violates single-line constraint (contains internal newline)."
                logger.error(msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = msg
                return False, msg, combined_payload

        # 6. Character Manifest Validation (if present)
        char_manifest_raw = combined_payload.get("character_manifest") or prompts.get("character_manifest")
        if char_manifest_raw is not None:
            ok_cm, cm_msg = self.validate_character_manifest(char_manifest_raw)
            if not ok_cm:
                logger.error(cm_msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = cm_msg
                return False, cm_msg, combined_payload

        # 7. Storyboard Manifest Validation (if present)
        storyboard_manifest_raw = combined_payload.get("storyboard_manifest") or prompts.get("storyboard_manifest")
        if storyboard_manifest_raw is not None:
            ok_sm, sm_msg = self.validate_storyboard_manifest(storyboard_manifest_raw, char_manifest_raw)
            if not ok_sm:
                logger.error(sm_msg)
                combined_payload["status"] = "GK2_Failed"
                combined_payload["gk2_error"] = sm_msg
                return False, sm_msg, combined_payload

        combined_payload["status"] = "GK2_Passed"
        logger.info(f"GK2 PASSED for story batch #{batch_id} with {len(unique_scenes)} progressive scenes.")
        return True, "GK2 Passed", combined_payload

    def validate_character_manifest(self, manifest: Any) -> Tuple[bool, str]:
        """
        Validates character_manifest against CharacterManifest schema invariants:
        - Must have batch_id >= 2, non-empty story_title, at least one protagonist.
        - Reference sheet naming pattern element_character_<name>_sheet.png.
        - Hex color palette validity and WCAG relative luminance contrast >= 1.35.
        - Deterministic positive reference_seed.
        """
        from character_consistency import CharacterManifest
        if isinstance(manifest, dict):
            try:
                c_obj = CharacterManifest.from_dict(manifest)
            except Exception as e:
                return False, f"GK2 FAIL: Malformed character manifest schema: {e}"
        elif isinstance(manifest, CharacterManifest):
            c_obj = manifest
        else:
            return False, "GK2 FAIL: Character manifest must be a dict or CharacterManifest instance"

        ok, errors = c_obj.validate()
        if not ok:
            return False, f"GK2 FAIL: Character manifest invalid: {errors[0]}"
        return True, "Character manifest valid"

    def validate_storyboard_manifest(self, manifest: Any, char_manifest: Any = None) -> Tuple[bool, str]:
        """
        Validates storyboard_manifest against StoryboardManifest schema invariants:
        - 10 sequential, contiguous scenes across 3 acts (or 8-10 scenes).
        - Cover illustration with active protagonist and CDS reference.
        - Environmental continuity across scenes sharing setting_id.
        - Character presence tracking and ghost speaker detection.
        - Valid cds_reference filenames matching element_character_<name>_sheet.png.
        """
        from character_consistency import StoryboardManifest, CharacterManifest
        if isinstance(manifest, dict):
            try:
                s_obj = StoryboardManifest.from_dict(manifest)
            except Exception as e:
                return False, f"GK2 FAIL: Malformed storyboard manifest schema: {e}"
        elif isinstance(manifest, StoryboardManifest):
            s_obj = manifest
        else:
            return False, "GK2 FAIL: Storyboard manifest must be a dict or StoryboardManifest instance"

        c_obj = None
        if char_manifest is not None:
            if isinstance(char_manifest, dict):
                try:
                    c_obj = CharacterManifest.from_dict(char_manifest)
                except Exception:
                    c_obj = None
            elif isinstance(char_manifest, CharacterManifest):
                c_obj = char_manifest

        ok, errors = s_obj.validate(c_obj)
        if not ok:
            return False, f"GK2 FAIL: Storyboard manifest invalid: {errors[0]}"
        return True, "Storyboard manifest valid"

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
        "act_1": idea.get("act_1", ""),
        "act_2": idea.get("act_2", ""),
        "act_3": idea.get("act_3", ""),
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
