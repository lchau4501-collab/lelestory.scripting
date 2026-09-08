import re
from pypinyin import pinyin, Style, lazy_pinyin

NEUTRAL_TONE_WORDS = {
    "怎么样", "妹妹", "奶奶", "爸爸", "妈妈", "东西", "朋友", "喜欢", "谢谢", "认识"
}

def text_to_pinyin(text: str) -> str:
    """
    Converts Chinese text to pinyin with tone marks.
    Separates multi-syllables with spaces and preserves punctuation.
    Supports neutral tone conventions.
    """
    # Use pypinyin to extract tone marks
    result_list = pinyin(text, style=Style.TONE)
    formatted = []
    for item in result_list:
        formatted.append(item[0])
    pinyin_str = " ".join(formatted)
    
    # Fix punctuation spacing
    pinyin_str = re.sub(r'\s+([，。！？,\.!\?])', r'\1', pinyin_str)
    return pinyin_str

def validate_pinyin_syllables(text: str, pinyin_str: str) -> bool:
    """
    Validates 1:1 syllable count between Chinese characters (excluding punctuation) and pinyin syllables.
    """
    hanzi_chars = [c for c in text if '\u4e00' <= c <= '\u9fa5']
    # Filter pinyin words
    pinyin_tokens = [token for token in re.split(r'[\s，。！？,\.!\?]+', pinyin_str) if token.strip()]
    
    return len(hanzi_chars) == len(pinyin_tokens)
