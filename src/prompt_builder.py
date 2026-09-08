import logging
from typing import Dict, Any, List

logger = logging.getLogger("lelestory.scripting")

class PromptBuilder:
    def __init__(self, script_payload: Dict[str, Any]):
        self.batch_id = script_payload.get("batch_id", 1)
        self.post_id = f"POST{self.batch_id:03d}"
        self.theme = script_payload.get("theme", "HANZIDEGUSHI")
        self.topic = script_payload.get("topic", "")
        self.hanzi = script_payload.get("hanzi_target", "")

    def build_prompts(self) -> Dict[str, Any]:
        """Builds structured image prompts with prefix convention [PLATFORM-POSTID-SLIDE-RATIO-STYLE]."""
        prompts = {
            "pinterest_mindmap": f"[PIN-{self.post_id}-S1-2x3-ST1] | Clean minimalist vertical infographic mindmap comparing Chinese character '{self.hanzi}', topic '{self.topic}', pastel tone, clear layout, cute mascot LeLe illustration.",
            "instagram_carousel": [
                f"[IG-{self.post_id}-SLIDE1-1x1-ST2] | Cute mascot LeLe presenting title '{self.topic}', modern pastel flat art background.",
                f"[IG-{self.post_id}-SLIDE2-1x1-ST2] | Detailed breakdown for character '{self.hanzi}', radical decomposition, clear typography.",
                f"[IG-{self.post_id}-SLIDE3-1x1-ST2] | Real-life sentence context example for '{self.hanzi}' with mascot LeLe reacting.",
                f"[IG-{self.post_id}-SLIDE4-1x1-ST2] | Common mistakes & memory trick visual guide.",
                f"[IG-{self.post_id}-SLIDE5-1x1-ST2] | Call-to-action slide: 'Comment TÀI LIỆU to receive full PDF mindmap', mascot LeLe waving."
            ],
            "facebook_durex_meme": f"[FB-{self.post_id}-GRID1-16x9-ST3] | Minimalist double-layer humorous visual depicting topic '{self.topic}', high contrast red and blue tones, AHA-moment concept.",
            "flashcard_anatomy": f"[FB-{self.post_id}-CARD1-1x1-ST4] | HSK Flashcard anatomy, big bold character '{self.hanzi}' in center, pinyin and stroke order diagram.",
            "comic_scene": f"[FB-{self.post_id}-COMIC1-4x3-ST5] | Real-life Chinese dialogue scene comic illustration for topic '{self.topic}', vibrant cartoon style."
        }
        logger.info(f"Built visual prompts for batch {self.post_id}")
        return prompts
