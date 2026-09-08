import json
import logging
from typing import Dict, Any, List
from pinyin_utils import text_to_pinyin
from multi_ai_provider import MultiAIProvider
import re

logger = logging.getLogger("lelestory.scripting")

class ScriptGenerator:
    def __init__(self, idea_data: Dict[str, Any]):
        self.idea_data = idea_data
        self.theme = idea_data.get("theme", "HANZIDEGUSHI")
        self.batch_id = idea_data.get("batch_id", 1)
        self.hanzi = idea_data.get("hanzi_target", "学习")
        self.concept = idea_data.get("concept_summary", "")
        self.ai = MultiAIProvider()

    def generate_script(self) -> Dict[str, Any]:
        """Generates line-by-line script payload using MultiAIProvider with template fallback."""
        prompt = f"""Generate a short educational dialogue for Chinese learners.
Topic/Hanzi: {self.hanzi} ({self.concept}).
Theme: {self.theme}.
Return STRICT JSON array with 3 to 4 dialogue lines:
[
  {{"speaker": "Narrator", "zh": "...", "vi": "..."}},
  {{"speaker": "LeLe", "zh": "...", "vi": "..."}}
]"""
        system_prompt = "You are an expert Chinese language teacher. Provide accurate Simplified Chinese and Vietnamese translations in valid JSON array only."
        
        raw_text = self.ai.call_ai(prompt, system_prompt)
        if raw_text:
            try:
                clean = re.sub(r"```(?:json)?", "", raw_text).replace("```", "").strip()
                parsed = json.loads(clean)
                if isinstance(parsed, list) and len(parsed) >= 2:
                    lines = []
                    for item in parsed:
                        zh = item.get("zh", "").strip()
                        vi = item.get("vi", "").strip()
                        spk = item.get("speaker", "LeLe")
                        if zh and vi:
                            lines.append({
                                "speaker": spk,
                                "zh": zh,
                                "pinyin": text_to_pinyin(zh),
                                "vi": vi
                            })
                    if len(lines) >= 2:
                        return {
                            "batch_id": self.batch_id,
                            "theme": self.theme,
                            "topic": self.idea_data.get("topic", ""),
                            "hanzi_target": self.hanzi,
                            "lines": lines,
                            "total_lines": len(lines),
                            "status": "Scripted",
                            "generator": "MultiAI_Live"
                        }
            except Exception:
                pass

        # Robust Fallback to Theme Templates
        lines = []

        if self.theme == "HANZIDEGUSHI":
            lines = [
                {"speaker": "Narrator", "zh": f"Bạn có biết nguồn gốc chữ {self.hanzi} không?", "pinyin": text_to_pinyin(f"Bạn có biết nguồn gốc chữ {self.hanzi} không?"), "vi": f"Bạn có biết nguồn gốc chữ {self.hanzi} không?"},
                {"speaker": "LeLe", "zh": f"Chữ {self.hanzi}: {self.concept}", "pinyin": text_to_pinyin(f"Chữ {self.hanzi}: {self.concept}"), "vi": f"Chữ {self.hanzi}: {self.concept}"},
                {"speaker": "LeLe", "zh": "Hãy cùng ghi nhớ chữ Hán này nhé!", "pinyin": text_to_pinyin("Hãy cùng ghi nhớ chữ Hán này nhé!"), "vi": "Hãy cùng ghi nhớ chữ Hán này nhé!"}
            ]
        elif self.theme == "IDIOMS":
            lines = [
                {"speaker": "Narrator", "zh": f"Thành ngữ hôm nay: {self.hanzi}", "pinyin": text_to_pinyin(self.hanzi), "vi": f"Thành ngữ: {self.concept}"},
                {"speaker": "LeLe", "zh": f"Ý nghĩa: {self.concept}", "pinyin": text_to_pinyin(self.concept), "vi": self.concept},
                {"speaker": "LeLe", "zh": "Áp dụng ngay vào giao tiếp nha!", "pinyin": text_to_pinyin("Áp dụng ngay vào giao tiếp nha!"), "vi": "Áp dụng ngay vào giao tiếp nha!"}
            ]
        elif self.theme == "SLANGS":
            lines = [
                {"speaker": "Narrator", "zh": f"Từ lóng hot trend: {self.hanzi}", "pinyin": text_to_pinyin(self.hanzi), "vi": f"Từ lóng: {self.concept}"},
                {"speaker": "Speaker A", "zh": f"最近我真的{self.hanzi}。", "pinyin": text_to_pinyin(f"Zuìjìn wǒ zhēnde {self.hanzi}."), "vi": f"Dạo này tôi thực sự {self.concept}."},
                {"speaker": "Speaker B", "zh": "加油！一切都会好起来的。", "pinyin": text_to_pinyin("Jiāyóu! Yīqiè dōuhuì hǎo qǐlái de."), "vi": "Cố lên! Mọi chuyện rồi sẽ tốt thôi."}
            ]
        elif self.theme == "VS_SERIES":
            lines = [
                {"speaker": "Narrator", "zh": f"Cặp từ dễ nhầm: {self.hanzi}", "pinyin": text_to_pinyin(self.hanzi), "vi": f"So sánh: {self.concept}"},
                {"speaker": "LeLe", "zh": f"Điểm cốt lõi: {self.concept}", "pinyin": text_to_pinyin(self.concept), "vi": self.concept},
                {"speaker": "LeLe", "zh": "Bạn đã phân biệt được chưa?", "pinyin": text_to_pinyin("Bạn đã phân biệt được chưa?"), "vi": "Bạn đã phân biệt được chưa?"}
            ]
        else: # DIALOGUES
            lines = [
                {"speaker": "Narrator", "zh": f"Hội thoại tình huống: {self.idea_data.get('topic', '')}", "pinyin": text_to_pinyin(self.idea_data.get('topic', '')), "vi": f"Chủ đề: {self.concept}"},
                {"speaker": "Speaker A", "zh": "你好！请问这个多少钱？", "pinyin": text_to_pinyin("Nǐ hǎo! Qǐngwèn zhège duōshǎo qián?"), "vi": "Xin chào! Cho hỏi cái này bao nhiêu tiền?"},
                {"speaker": "Speaker B", "zh": "这个五十块钱。", "pinyin": text_to_pinyin("Zhège wǔshí kuài qián."), "vi": "Cái này 50 tệ."},
                {"speaker": "Speaker A", "zh": "好的，我要一个。", "pinyin": text_to_pinyin("Hǎo de, wǒ yào yīgè."), "vi": "Được rồi, tôi lấy một cái."}
            ]

        script_payload = {
            "batch_id": self.batch_id,
            "theme": self.theme,
            "topic": self.idea_data.get("topic", ""),
            "hanzi_target": self.hanzi,
            "lines": lines,
            "total_lines": len(lines),
            "status": "Scripted"
        }
        logger.info(f"Script generated for batch #{self.batch_id} ({len(lines)} lines)")
        return script_payload
