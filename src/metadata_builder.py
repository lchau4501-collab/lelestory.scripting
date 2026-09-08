import logging
from typing import Dict, Any

logger = logging.getLogger("lelestory.scripting")

class MetadataBuilder:
    def __init__(self, script_payload: Dict[str, Any]):
        self.batch_id = script_payload.get("batch_id", 1)
        self.theme = script_payload.get("theme", "HANZIDEGUSHI")
        self.topic = script_payload.get("topic", "")
        self.hanzi = script_payload.get("hanzi_target", "")

    def build_metadata(self) -> Dict[str, Any]:
        """Builds multi-platform metadata titles, descriptions, and hashtags."""
        title = f"Học Tiếng Trung cùng Bé Lê Lê: {self.topic} (#{self.batch_id})"
        description = (
            f"Chủ đề hôm nay: {self.topic} ({self.hanzi}).\n"
            f"Cùng Bé Lê Lê chinh phục HSK dễ dàng mỗi ngày!\n"
            f"👇 Đừng quên Comment 'TÀI LIỆU' để nhận PDF bài học nhé!"
        )
        hashtags = ["#lelehoctiengtrung", "#tiengtrung", "#hsk", "#pinyin", f"#hsk{self.batch_id % 3 + 1}"]
        
        metadata = {
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "target_slots": ["07:00", "13:00", "19:00"],
            "formatted_caption": f"{title}\n\n{description}\n\n" + " ".join(hashtags)
        }
        logger.info(f"Built metadata for batch #{self.batch_id}")
        return metadata
