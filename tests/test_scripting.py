import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from pinyin_utils import text_to_pinyin
from script_generator import ScriptGenerator
from prompt_builder import PromptBuilder
from metadata_builder import MetadataBuilder
from gatekeeper2 import Gatekeeper2

def test_pinyin_conversion():
    py = text_to_pinyin("学习中文")
    assert "xué" in py or "xue" in py

def test_script_generator():
    idea = {
        "batch_id": 5,
        "theme": "HANZIDEGUSHI",
        "topic": "Chiết tự chữ 休",
        "hanzi_target": "休",
        "concept_summary": "Con người dựa vào cây"
    }
    sg = ScriptGenerator(idea)
    script = sg.generate_script()
    assert script["batch_id"] == 5
    assert len(script["lines"]) >= 3

def test_prompt_builder():
    script = {"batch_id": 5, "theme": "HANZIDEGUSHI", "topic": "Test", "hanzi_target": "休"}
    pb = PromptBuilder(script)
    prompts = pb.build_prompts()
    assert "instagram_carousel" in prompts
    assert prompts["instagram_carousel"][0].startswith("[IG-POST005-SLIDE1-1x1-ST2]")

def test_gatekeeper2_pass():
    idea = {
        "batch_id": 1,
        "theme": "HANZIDEGUSHI",
        "topic": "Chiết tự chữ 休",
        "hanzi_target": "休",
        "concept_summary": "Con người dựa vào cây"
    }
    sg = ScriptGenerator(idea)
    script_data = sg.generate_script()
    pb = PromptBuilder(script_data)
    prompts_data = pb.build_prompts()
    mb = MetadataBuilder(script_data)
    meta_data = mb.build_metadata()

    combined = {
        "batch_id": 1,
        "theme": "HANZIDEGUSHI",
        "script": script_data,
        "prompts": prompts_data,
        "metadata": meta_data,
        "status": "Pending_GK2"
    }
    gk2 = Gatekeeper2()
    passed, reason, updated = gk2.validate(combined)
    assert passed == True
    assert updated["status"] == "GK2_Passed"
