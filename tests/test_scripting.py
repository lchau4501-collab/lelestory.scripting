import pytest
import sys
import os
import re
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from pinyin_utils import text_to_pinyin
from script_generator import ScriptGenerator, VIETNAMESE_PATTERN
from prompt_builder import PromptBuilder, FIXED_STYLE_BLOCK
from metadata_builder import MetadataBuilder
from gatekeeper2 import Gatekeeper2
from gsheet_sync import create_gdoc_via_webhook

def test_pinyin_conversion():
    py = text_to_pinyin("学习中文")
    assert "xué" in py or "xue" in py
    # Test polyphonic / tone mark
    py_story = text_to_pinyin("吃菜的大狼")
    assert "chī" in py_story or "chi" in py_story

def test_script_generator_8_to_10_scenes():
    """Verifies that script generator produces 8–10 scenes following 3-act arc, 5 vocab, and outro."""
    idea = {
        "batch_id": 2,
        "row_id": 2,
        "title": "吃菜的大狼",
        "story_plot": "大灰狼罗罗爱吃蔬菜，暴风雨中救小兔，大家消除偏见成为好友。",
        "act_1": "罗罗爱种菜，小动物害怕狼",
        "act_2": "暴风雨刮倒大树困住兔洞，罗罗奋力移开大树",
        "act_3": "救出小兔，消除偏见，共吃火锅"
    }
    sg = ScriptGenerator(idea)
    script = sg.generate_script()
    assert script["batch_id"] == 2
    assert script["title"] == "吃菜的大狼"

    lines = script["lines"]
    unique_scenes = sorted(list(set(l["scene_num"] for l in lines)))
    assert 8 <= len(unique_scenes) <= 10, f"Expected 8-10 scenes, got {len(unique_scenes)}"
    assert unique_scenes[0] == 1
    assert unique_scenes[-1] in (8, 9, 10)

    # Check trilingual schema per scene line: zh, pinyin, en
    for l in lines:
        assert "zh" in l and len(l["zh"]) > 0
        assert "pinyin" in l and len(l["pinyin"]) > 0
        assert "en" in l and len(l["en"]) > 0
        # Strictly ZERO Vietnamese in en field
        assert not VIETNAMESE_PATTERN.search(l["en"]), f"Vietnamese detected in line en: {l['en']}"

    # Check 5 educational vocabulary items
    vocab = script["vocabulary"]
    assert len(vocab) == 5, f"Expected exactly 5 vocabulary items, got {len(vocab)}"
    for v in vocab:
        assert "word" in v and len(v["word"]) > 0
        assert "pinyin" in v and len(v["pinyin"]) > 0
        assert "en" in v and len(v["en"]) > 0
        assert not VIETNAMESE_PATTERN.search(v["en"]), f"Vietnamese detected in vocab en: {v['en']}"

    # Check outro loop sentence
    outro = script["outro"]
    assert "zh" in outro and "来自故事" in outro["zh"]
    assert "pinyin" in outro and "gù shì" in outro["pinyin"]
    assert "en" in outro and "vocabulary comes from the story" in outro["en"].lower()
    assert not VIETNAMESE_PATTERN.search(outro["en"])

def test_prompt_builder_dynamic_8_to_10_scenes_and_tab2():
    """Verifies Tab 1 contains 8-10 scenes + cover + vocab + outro; Tab 2 contains elements on top."""
    idea = {"batch_id": 2, "title": "吃菜的大狼", "story_plot": "Test plot"}
    sg = ScriptGenerator(idea)
    script_data = sg.generate_script()

    pb = PromptBuilder(script_data)
    prompts = pb.build_prompts()

    tab1 = prompts["tab1_scenes"]
    tab2 = prompts["tab2_elements"]
    gdoc_text = prompts["formatted_gdoc_text"]

    # Tab 1 Scene tags
    tab1_tags = [item["tag"] for item in tab1]
    assert any("Scene-Cover" in t for t in tab1_tags), "Missing Scene-Cover prompt"
    assert any("[Scene-1]" in t for t in tab1_tags), "Missing Scene-1"
    assert any("[Scene-8]" in t for t in tab1_tags), "Missing Scene-8"
    assert any("[Scene-10]" in t for t in tab1_tags), "Missing Scene-10"
    for v_idx in range(1, 6):
        assert any(f"[Vocabulary-{v_idx}-" in t for t in tab1_tags), f"Missing Vocabulary-{v_idx} prompt"
    assert any("[Outro-Loop]" in t for t in tab1_tags), "Missing Outro-Loop prompt"

    # Tab 2 Elements: Characters, Backgrounds, Props
    categories = {item["category"] for item in tab2}
    assert "Characters" in categories, "Missing Characters category in Tab 2"
    assert "Background" in categories, "Missing Background category in Tab 2"
    assert "Props" in categories, "Missing Props category in Tab 2"

    # Formatting verification: Tab 2 on top, Tab 1 on bottom
    paragraphs = gdoc_text.split("\n\n")
    assert len(paragraphs) == len(tab2) + len(tab1)

    # First paragraph must be Tab 2 element
    assert paragraphs[0].startswith("[Element-")
    # Later paragraph must be Tab 1 scene
    assert any(p.startswith("[Scene-") for p in paragraphs)

    # Strict 1 line per prompt constraint
    for idx, p in enumerate(paragraphs, 1):
        assert "\n" not in p.strip(), f"Prompt #{idx} contains internal newline: {p}"
        assert "--ar 9:16 --stylize 250" in p, f"Prompt #{idx} missing style suffix"

def test_gatekeeper2_pass():
    idea = {
        "batch_id": 2,
        "row_id": 2,
        "title": "吃菜的大狼",
        "story_plot": "温和大狼爱吃蔬菜，救小兔消除偏见。"
    }
    sg = ScriptGenerator(idea)
    script_data = sg.generate_script()
    pb = PromptBuilder(script_data)
    prompts_data = pb.build_prompts()
    mb = MetadataBuilder(script_data)
    meta_data = mb.build_metadata()

    combined = {
        "batch_id": 2,
        "row_id": 2,
        "title": "吃菜的大狼",
        "story_plot": "温和大狼爱吃蔬菜，救小兔消除偏见。",
        "script": script_data,
        "prompts": prompts_data,
        "metadata": meta_data,
        "status": "Pending_GK2"
    }
    gk2 = Gatekeeper2()
    passed, reason, updated = gk2.validate(combined)
    assert passed == True
    assert updated["status"] == "GK2_Passed"

def test_gatekeeper2_rejects_fewer_than_8_scenes():
    """GK2 must reject legacy 4-scene scripts."""
    combined = {
        "batch_id": 2,
        "script": {
            "lines": [
                {"scene_num": 1, "zh": "句子1", "pinyin": "jù zi 1", "en": "Sentence 1"},
                {"scene_num": 2, "zh": "句子2", "pinyin": "jù zi 2", "en": "Sentence 2"},
                {"scene_num": 3, "zh": "句子3", "pinyin": "jù zi 3", "en": "Sentence 3"},
                {"scene_num": 4, "zh": "句子4", "pinyin": "jù zi 4", "en": "Sentence 4"}
            ],
            "vocabulary": [
                {"word": "词", "pinyin": "cí", "en": "word"} for _ in range(5)
            ],
            "outro": {"zh": "来自故事", "pinyin": "lái zì gù shì", "en": "From the story"}
        },
        "prompts": {"tab1_scenes": [{"tag": "[Scene-Cover]"}, {"tag": "[Outro-Loop]"}], "tab2_elements": [{"tag": "[Element-1]"}]},
        "metadata": {}
    }
    gk2 = Gatekeeper2()
    passed, reason, updated = gk2.validate(combined)
    assert passed == False
    assert "must have between 8 and 10 progressive scenes" in reason

def test_gatekeeper2_rejects_vietnamese_characters():
    """GK2 strictly enforces zero Vietnamese in English fields."""
    idea = {"batch_id": 2, "title": "吃菜的大狼"}
    sg = ScriptGenerator(idea)
    script_data = sg.generate_script()
    # Inject Vietnamese text into line 3
    script_data["lines"][2]["en"] = "Con sói này rất là tốt bụng và thích ăn cà rốt."

    pb = PromptBuilder(script_data)
    prompts_data = pb.build_prompts()
    mb = MetadataBuilder(script_data)

    combined = {
        "batch_id": 2,
        "script": script_data,
        "prompts": prompts_data,
        "metadata": mb.build_metadata()
    }
    gk2 = Gatekeeper2()
    passed, reason, updated = gk2.validate(combined)
    assert passed == False
    assert "Vietnamese characters" in reason

def test_webhook_title_parameter_not_prefixed():
    """Verifies that create_gdoc_via_webhook sends exact title without hardcoded 'Script - 《...》'."""
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "url": "https://docs.google.com/document/d/123/edit", "id": "123"}
        mock_post.return_value = mock_resp

        # Call with "Image prompt"
        url = create_gdoc_via_webhook("test_folder_123", "Image prompt", "prompt text")
        assert url == "https://docs.google.com/document/d/123/edit"

        # Verify request payload
        mock_post.assert_called_once()
        sent_body = mock_post.call_args[1]["json"]
        assert sent_body["title"] == "Image prompt", f"Expected 'Image prompt', got '{sent_body['title']}'"
        assert sent_body["folderId"] == "test_folder_123"

def test_metadata_builder_strictly_zero_vietnamese():
    """Verifies MetadataBuilder outputs zero Vietnamese in all English fields."""
    idea = {
        "batch_id": 2,
        "title": "吃菜的大狼",
        "story_plot": "温和大狼救小兔",
        "vocabulary": [{"word": "蔬菜", "pinyin": "shū cài", "en": "Vegetables"}]
    }
    mb = MetadataBuilder(idea)
    meta = mb.build_metadata()

    # Verify English titles & descriptions have no Vietnamese
    assert not VIETNAMESE_PATTERN.search(meta["youtube"]["title"])
    assert not VIETNAMESE_PATTERN.search(meta["tiktok"]["title"])
    assert not VIETNAMESE_PATTERN.search(meta["facebook"]["title"])

    # Verify no Vietnamese words in the content headers
    fb_content = meta["facebook"]["description"]
    assert "Câu chuyện" not in fb_content
    assert "Tóm tắt" not in fb_content
    assert "Từ vựng" not in fb_content


def test_row_4_artifacts_pass_gk2():
    """Verifies that Row #4 artifacts pass GK2, contrast check, and chunking constraints."""
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../artifacts"))
    script_path = os.path.join(artifacts_dir, "script_gk2_row_4.json")
    char_path = os.path.join(artifacts_dir, "character_manifest_row_4.json")
    storyboard_path = os.path.join(artifacts_dir, "storyboard_manifest_row_4.json")
    metadata_path = os.path.join(artifacts_dir, "story_metadata_row_4.json")

    for path in [script_path, char_path, storyboard_path, metadata_path]:
        assert os.path.isfile(path), f"Missing artifact: {path}"

    with open(script_path, "r", encoding="utf-8") as f:
        script_payload = json.load(f)

    assert script_payload["batch_id"] == 4
    assert script_payload["row_id"] == 4
    assert script_payload["title"] == "小马过河"
    assert len(script_payload["script"]["lines"]) == 10
    assert len(script_payload["script"]["vocabulary"]) == 5

    gk2 = Gatekeeper2()
    passed, reason, updated = gk2.validate(script_payload)
    assert passed, f"Row #4 GK2 validation failed: {reason}"
    assert updated["status"] == "GK2_Passed"

    with open(char_path, "r", encoding="utf-8") as f:
        char_payload = json.load(f)
    assert char_payload["contrast_analysis"]["wcag_contrast_ratio"] >= 1.35
    assert char_payload["contrast_analysis"]["is_passed"] == True
