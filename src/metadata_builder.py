import logging
from typing import Dict, Any

logger = logging.getLogger("lelestory.scripting")

class MetadataBuilder:
    def __init__(self, script_payload: Dict[str, Any]):
        self.batch_id = script_payload.get("batch_id", 2)
        self.title = script_payload.get("title", "吃菜的大狼")
        self.plot = script_payload.get("story_plot", "")
        self.vocab = script_payload.get("vocabulary", [])

    def build_metadata(self) -> Dict[str, Any]:
        """Builds multi-platform metadata titles and descriptions for YouTube, TikTok, and Facebook."""
        vocab_str = ", ".join([f"{v.get('word')} ({v.get('en')})" for v in self.vocab])
        hashtags_str = "#lelehoctiengtrung #hsk #hoctiengtrung #chinesestory"

        # YouTube
        yt_title = f"《{self.title}》- Learn Chinese Through Storybooks (#{self.batch_id})"
        yt_desc = (
            f"Story Title: 《{self.title}》\n"
            f"Story Synopsis: {self.plot}\n\n"
            f"Key Chinese Vocabulary: {vocab_str}\n\n"
            f"Learn Chinese with LeLe Storybook Video Engine! Follow along with natural Pinyin and English subtitles.\n\n"
            f"{hashtags_str}"
        )

        # TikTok
        tt_title = f"《{self.title}》Learn Chinese Fast (#{self.batch_id})"
        tt_caption = f"Story: 《{self.title}》- {self.plot[:80]}... Vocabulary: {vocab_str} {hashtags_str}"

        # Facebook
        fb_title = f"Chinese Storybook #{self.batch_id}: 《{self.title}》"
        fb_desc = (
            f"🏮 Câu chuyện tiếng Trung hôm nay: 《{self.title}》\n\n"
            f"📖 Tóm tắt / Plot: {self.plot}\n\n"
            f"💡 Từ vựng trọng điểm / Key Vocabulary:\n"
            + "\n".join([f"• {v.get('word')} ({v.get('pinyin')}): {v.get('en')}" for v in self.vocab])
            + f"\n\n{hashtags_str}"
        )

        formatted_metadata_txt = (
            f"【YOUTUBE METADATA】\n"
            f"Title: {yt_title}\n\n"
            f"Description:\n{yt_desc}\n\n"
            f"----------------------------------------\n"
            f"【TIKTOK METADATA】\n"
            f"Title: {tt_title}\n\n"
            f"Caption:\n{tt_caption}\n\n"
            f"----------------------------------------\n"
            f"【FACEBOOK METADATA】\n"
            f"Title: {fb_title}\n\n"
            f"Post Content:\n{fb_desc}\n"
        )

        return {
            "youtube": {"title": yt_title, "description": yt_desc},
            "tiktok": {"title": tt_title, "caption": tt_caption},
            "facebook": {"title": fb_title, "description": fb_desc},
            "hashtags": hashtags_str.split(),
            "formatted_metadata_txt": formatted_metadata_txt
        }
