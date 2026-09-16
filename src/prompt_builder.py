import logging
import re
from typing import Dict, Any, List, Set, Tuple

from character_consistency import (
    CharacterConsistencyEngine,
    CharacterManifest,
    StoryboardManifest,
)

logger = logging.getLogger("lelestory.scripting")

ANATOMY_PROTECTION_KEYWORDS = (
    "anatomically correct four legs, exactly four hooves, natural quadruped posture"
)

STANDARDIZED_NEGATIVE_PROMPT = (
    "--no extra limbs, 6 legs, deformed legs, mutated anatomy, bad anatomy, "
    "duplicate legs, fused legs, missing limbs, deformed hooves, extra ears, mutated fingers, "
    "text, watermark, subtitles, signature, letters"
)

BASE_ART_STYLE_BLOCK = (
    "charming watercolor storybook illustration, whimsical children's book art style, "
    "hand-drawn aesthetic, soft textured paper background, warm soft pastel color palette, "
    "gentle sunlit fairytale lighting, cozy hygge mood, Studio Ghibli inspired warmth, "
    "vertical 9:16 composition, main subjects focused in upper and middle frame, "
    "clean uncluttered lower third for text overlay --ar 9:16 --stylize 250"
)

FIXED_STYLE_BLOCK = (
    "charming watercolor storybook illustration, whimsical children's book art style, "
    "hand-drawn aesthetic, soft textured paper background, warm soft pastel color palette, "
    "gentle sunlit fairytale lighting, cozy hygge mood, Studio Ghibli inspired warmth, "
    "vertical 9:16 composition, main subjects focused in upper and middle frame, "
    f"clean uncluttered lower third for text overlay {STANDARDIZED_NEGATIVE_PROMPT} --ar 9:16 --stylize 250"
)

PROMPT_POISON_PATTERNS = [
    # Subtitle injections: 'show subtitle ...', 'subtitles saying ...'
    r'(?:,\s*)?(?:show|display|add|with)?\s*(?:a\s+)?subtitles?(?:\s+saying|\s+showing|\s+reading|\s+in|\s+with|\s*[:\'\"]).*?(?=[,;.]|$)',
    # Dialogue / speech bubbles: 'with a dialogue text bubble saying ...', 'speech bubble with ...'
    r'(?:,\s*)?(?:with\s+)?(?:a\s+)?(?:dialogue|speech|text)\s+(?:text\s+)?(?:bubble|box)(?:\s+saying|\s+reading|\s+with|\s*[:\'\"]).*?(?=[,;.]|$)',
    # Text / English / Chinese labels / written names: 'with English label ...', 'with written name ...'
    r'(?:,\s*)?(?:with\s+)?(?:an?\s+)?(?:english|chinese|text|written)?\s*(?:label|title|caption|name)(?:\s+saying|\s+written|\s+reading|\s+in|\s*[:\'\"]).*?(?=[,;.]|$)',
    # Character / Hanzi painting requests: 'please paint the Chinese characters ...'
    r'(?:,\s*)?(?:please\s+)?(?:paint|draw|write|render|display)\s+(?:the\s+)?(?:chinese\s+characters?|hanzi|pinyin|letters?|words?|text)\b.*?(?=[,;.]|$)',
    # Floating words or explicit written text: 'written text: ...', 'words floating ...'
    r'(?:,\s*)?(?:with\s+)?(?:written\s+text\s*:?|written\s+name\s*:?|words\s+floating|text\s+saying)\b.*?(?=[,;.]|$)',
    # 'written across the bottom ...'
    r'(?:,\s*)?written\s+across\b.*?(?=[,;.]|$)',
]

def sanitize_prompt_text(text: str) -> str:
    """
    Strips prompt-poisoning phrases (subtitle requests, speech/dialogue bubbles,
    labels, and explicit text-drawing instructions) to prevent prompt injection.
    """
    if not text:
        return ""
    cleaned = str(text)
    for pattern in PROMPT_POISON_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*,\s*,+", ",", cleaned)
    cleaned = re.sub(r"^\s*[,;.-]+\s*", "", cleaned)
    cleaned = re.sub(r"\s*[,;.-]+\s*$", "", cleaned)
    cleaned = re.sub(r"\b(?:with|in|and|or)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*[,;.-]+\s*$", "", cleaned)
    return " ".join(cleaned.split())

DEFAULT_NARRATIVE_SCENES = [
    (1, "World setup introducing the peaceful fairytale land and central characters."),
    (2, "The main character discovers an unexpected curiosity or gentle call to adventure."),
    (3, "Venturing deeper into the enchanted storybook environment with friends."),
    (4, "A playful puzzle or meaningful challenge appears along the forest path."),
    (5, "Collaborating warmly to discover a creative, heartwarming solution."),
    (6, "Overcoming the hurdle with patience, teamwork, and kindness."),
    (7, "A joyous gathering celebrating the accomplishment with shared warmth."),
    (8, "Peaceful evening twilight settling over the cozy fairytale home."),
]

DEFAULT_VOCABULARY = [
    {"word": "蔬菜", "en": "vegetables"},
    {"word": "森林", "en": "forest"},
    {"word": "朋友", "en": "friend"},
    {"word": "太阳", "en": "sun"},
    {"word": "快乐", "en": "happiness"},
]

def build_cover_prompt(self_or_title: Any = None, title: str = None) -> str:
    """
    Builds modernized 100% pure visual zero-text cover image prompt conforming to 2026-09-15 locked specification:
    Strictly zero text / typography in the graphic image (no letters, no words, no watermark, no title text),
    with pure watercolor paper background, leaving clean uncluttered lower third for Stage 5 video title (160px)
    and brand watermark overlay.
    """
    t = title
    if t is None:
        if isinstance(self_or_title, str):
            t = self_or_title
        elif hasattr(self_or_title, "title"):
            t = getattr(self_or_title, "title", None)
    clean_title = re.sub(r"[《》\s]", "", str(t or "吃菜的大狼")) or "吃菜的大狼"
    return (
        f"Charming storybook cover illustration representing the story '{clean_title}', "
        f"whimsical main characters featured warmly in a magical fairytale landscape, soft glowing sunbeams, "
        f"pure visual storybook illustration without text, strictly zero text in graphic, no letters, no words, "
        f"charming watercolor storybook illustration, whimsical children's book art style, "
        f"hand-drawn aesthetic, pure watercolor paper background, soft textured paper background, warm soft pastel color palette, "
        f"gentle sunlit fairytale lighting, cozy hygge mood, Studio Ghibli inspired warmth, "
        f"vertical 9:16 composition, main subjects focused in upper and middle frame, "
        f"clean uncluttered lower third for text overlay, "
        f"{ANATOMY_PROTECTION_KEYWORDS} "
        f"--no text, watermark, letters, words, subtitles, title text, extra limbs, 6 legs, deformed legs, "
        f"mutated anatomy, bad anatomy, duplicate legs, fused legs, missing limbs, deformed hooves, extra ears, mutated fingers, "
        f"signature --ar 9:16 --stylize 250"
    )

def build_scene_prompt(*args, **kwargs) -> str:
    """
    Builds scene image prompt with strict text ban, anatomy protection, and prompt injection sanitization.
    Supports:
      build_scene_prompt(scene_num, description)
      build_scene_prompt(self, scene_num, description)
      build_scene_prompt(scene_num=1, description="...")
    """
    pos_args = list(args)
    if pos_args and hasattr(pos_args[0], "build_prompts"):
        pos_args.pop(0)

    s_num = kwargs.get("scene_num")
    desc = kwargs.get("description", "")

    if pos_args:
        if s_num is None:
            s_num = pos_args[0]
        if len(pos_args) > 1 and not desc:
            desc = pos_args[1]

    if s_num is None:
        s_num = 1
    try:
        s_num = int(s_num)
    except (ValueError, TypeError):
        s_num = 1

    clean_desc = sanitize_prompt_text(desc or "")
    if not clean_desc:
        clean_desc = f"Story scene {s_num} portraying key narrative moment."
    if len(clean_desc) > 220:
        clean_desc = clean_desc[:217] + "..."

    return (
        f"Scene {s_num}: {clean_desc}, {ANATOMY_PROTECTION_KEYWORDS}, "
        f"strictly zero text in artwork, no letters, no words, no subtitles (natural in-world environment signs permitted), "
        f"{FIXED_STYLE_BLOCK}"
    )

def build_vocab_prompt(*args, **kwargs) -> str:
    """
    Builds vocab flashcard image prompt enforcing 100% pure standalone illustration in focal upper 40% area.
    Supports:
      build_vocab_prompt(index, word, definition_en)
      build_vocab_prompt(self, index, word, definition_en)
      build_vocab_prompt(index=1, word="蔬菜", definition_en="vegetables")
    """
    pos_args = list(args)
    if pos_args and hasattr(pos_args[0], "build_prompts"):
        pos_args.pop(0)

    idx = kwargs.get("index")
    w = kwargs.get("word", "")
    en = kwargs.get("definition_en", "")

    if pos_args:
        if idx is None:
            idx = pos_args[0]
        if len(pos_args) > 1 and not w:
            w = pos_args[1]
        if len(pos_args) > 2 and not en:
            en = pos_args[2]

    if idx is None:
        idx = 1
    try:
        idx = int(idx)
    except (ValueError, TypeError):
        idx = 1

    clean_w = str(w or "").strip()
    clean_en = sanitize_prompt_text(en or "")
    if not clean_en:
        clean_en = "vocabulary item"

    return (
        f"Educational storybook flashcard visual featuring '{clean_w}' ({clean_en}), "
        f"100% pure standalone illustration in focal upper 40% area, strictly zero text in graphic, "
        f"centered iconic circular illustration with whimsical hand-painted details, soft pastel background, "
        f"{ANATOMY_PROTECTION_KEYWORDS}, "
        f"{FIXED_STYLE_BLOCK}"
    )

def build_outro_prompt(*args, **kwargs) -> str:
    """Builds outro loop image prompt enforcing zero text and anatomy protection."""
    return (
        f"Heartwarming storybook outro illustration showing the characters smiling and waving warmly towards the viewer, "
        f"{ANATOMY_PROTECTION_KEYWORDS}, "
        f"strictly zero text in graphic, cozy conclusion scene with soft glowing fairytale twilight lanterns, "
        f"{FIXED_STYLE_BLOCK}"
    )

def build_sd_negative_prompt() -> str:
    """Returns comprehensive negative tokens for Stable Diffusion / Image Gen."""
    return (
        "extra limbs, 6 legs, deformed legs, mutated anatomy, bad anatomy, "
        "duplicate legs, fused legs, missing limbs, deformed hooves, extra ears, mutated fingers, "
        "text, watermark, subtitles, signature, letters, logo, dialogue box, banners, caption, low quality"
    )

def audit_prompt_text_rules(tag: str, prompt: str) -> Tuple[bool, str]:
    """Audits prompt text rules: enforces strict zero in-image text on Cover, Scenes, Vocab, and Outro."""
    p_lower = prompt.lower()
    tag_lower = tag.lower()

    banned_requests = [
        "with english title", "show subtitle", "written text:", "words floating",
        "dialogue bubble", "dialogue text bubble", "english label", "written across",
        "paint the chinese characters", "stylized english"
    ]
    for b in banned_requests:
        if b in p_lower:
            return False, f"Forbidden text request '{b}' in {tag}"

    if not any(k in p_lower for k in ["no text", "zero text", "pure illustration", "pure visual", "pure standalone illustration", "without text"]):
        return False, f"Missing negative text guardrail in {tag}"
    return True, "OK"

class PromptBuilder:
    def __init__(self, script_payload: Dict[str, Any]):
        if not isinstance(script_payload, dict):
            script_payload = {}
        self.batch_id = script_payload.get("batch_id") or script_payload.get("row_id") or 2
        self.title = script_payload.get("title") or "吃菜的大狼"
        self.plot = script_payload.get("story_plot") or ""
        self.lines = script_payload.get("lines") or []
        self.vocab = script_payload.get("vocabulary") or []
        self.outro = script_payload.get("outro") or {}
        self.char_manifest = CharacterConsistencyEngine.generate_character_manifest(script_payload)
        self.storyboard_manifest = CharacterConsistencyEngine.generate_storyboard_manifest(script_payload, self.char_manifest)

    def build_cover_prompt(self, title: str = None) -> str:
        return build_cover_prompt(title or self.title)

    def build_scene_prompt(self, scene_num: int, description: str = "") -> str:
        return build_scene_prompt(scene_num, description)

    def build_vocab_prompt(self, index: int, word: str, definition_en: str = "") -> str:
        return build_vocab_prompt(index, word, definition_en)

    def build_outro_prompt(self) -> str:
        return build_outro_prompt()

    @staticmethod
    def build_sd_negative_prompt() -> str:
        return build_sd_negative_prompt()

    def build_prompts(self) -> Dict[str, Any]:
        """
        Builds Tab 1 (Scenes 1..N where N=8..10, Vocab 1..5, Outro-Loop)
        and Tab 2 (Elements: Characters, Backgrounds, Props) image prompts.
        Enforces strict single-line format, Tab 2 on top, Tab 1 on bottom, separated by double newlines.
        """
        tab2_elements = self._build_dynamic_tab2_elements()
        tab1_scenes = self._build_dynamic_tab1_scenes()

        # Format: Tab 2 on top, Tab 1 below, exactly 1 blank line between, 1 line per prompt
        all_prompt_lines = []
        for item in tab2_elements:
            clean_prompt = " ".join(item["prompt"].split())
            all_prompt_lines.append(f"{item['tag']} {clean_prompt}")

        for item in tab1_scenes:
            clean_prompt = " ".join(item["prompt"].split())
            all_prompt_lines.append(f"{item['tag']} {clean_prompt}")

        formatted_gdoc_text = "\n\n".join(all_prompt_lines)

        return {
            "tab1_scenes": tab1_scenes,
            "tab2_elements": tab2_elements,
            "formatted_gdoc_text": formatted_gdoc_text,
            "fixed_style": FIXED_STYLE_BLOCK,
            "character_manifest": self.char_manifest.to_dict() if hasattr(self, "char_manifest") and self.char_manifest else {},
            "storyboard_manifest": self.storyboard_manifest.to_dict() if hasattr(self, "storyboard_manifest") and self.storyboard_manifest else {}
        }

    def _build_dynamic_tab2_elements(self) -> List[Dict[str, str]]:
        """
        Dynamically extracts and constructs comprehensive Tab 2 element prompts:
        - All characters (main protagonists, antagonists, woodland friends, supporting cast with multiple poses/emotions)
        - Key narrative backgrounds across all scenes
        - Key props from vocabulary and narrative items
        """
        elements = []

        # 1. Characters: Extract ALL unique characters and speakers from the story
        speakers: List[str] = []
        for line in self.lines:
            if not isinstance(line, dict):
                continue
            spk = (line.get("speaker") or "").strip()
            if spk and spk != "Narrator" and spk not in speakers:
                speakers.append(spk)

        # Also extract any mentioned character names in the story plot or title if missing
        if not speakers:
            speakers = ["主人公", "好朋友", "配角"]

        # Generate comprehensive character elements for every character
        if hasattr(self, "char_manifest") and self.char_manifest:
            for c in self.char_manifest.characters:
                clean_sheet_tag = c.name_zh or c.name_en or c.character_id
                sheet_prompt = CharacterConsistencyEngine.generate_character_design_sheet_prompt(c)
                elements.append({
                    "category": "Characters",
                    "tag": f"[Element-Character-{clean_sheet_tag}-Sheet]",
                    "prompt": sheet_prompt
                })

        for spk in speakers:
            clean_tag = re.sub(r"[^\w\u4e00-\u9fa5]", "", spk) or "Character"
            # Neutral / Standing Reference
            elements.append({
                "category": "Characters",
                "tag": f"[Element-Character-{clean_tag}-Neutral]",
                "prompt": f"Storybook character portrait of {spk}, neutral standing pose, expressive and lovable children's book design, centered on clean textured paper background, {FIXED_STYLE_BLOCK}"
            })
            # Expressive / Emotion & Action Reference
            elements.append({
                "category": "Characters",
                "tag": f"[Element-Character-{clean_tag}-Expressive]",
                "prompt": f"Storybook character portrait of {spk} with joyful and warm facial expression, dynamic cute action pose, {FIXED_STYLE_BLOCK}"
            })

        # Ensure supporting woodland/fairytale friend is present if only 1 character
        if len(speakers) == 1:
            elements.append({
                "category": "Characters",
                "tag": "[Element-Character-Friend-Cute]",
                "prompt": f"Storybook character portrait of a friendly and lovable woodland animal companion, cheerful smile, {FIXED_STYLE_BLOCK}"
            })

        # 2. Backgrounds: Distinct narrative environments matching story progression
        elements.append({
            "category": "Background",
            "tag": "[Element-Background-ForestClearing]",
            "prompt": f"A peaceful, sun-dappled fairy tale forest clearing with quaint storybook trees and vibrant wildflower meadow, soft morning sunlight, {FIXED_STYLE_BLOCK}"
        })
        elements.append({
            "category": "Background",
            "tag": "[Element-Background-CozyCottageInterior]",
            "prompt": f"A warm and cozy rustic wooden living room inside a fairytale cabin, wooden table, soft hearth glow, warm ambient fairytale lighting, {FIXED_STYLE_BLOCK}"
        })
        elements.append({
            "category": "Background",
            "tag": "[Element-Background-AdventurePath]",
            "prompt": f"A scenic winding fairytale trail across gentle rolling green hills under a bright pastel blue sky with fluffy clouds, {FIXED_STYLE_BLOCK}"
        })
        elements.append({
            "category": "Background",
            "tag": "[Element-Background-SunsetCelebration]",
            "prompt": f"A festive storybook gathering glade at golden hour sunset, glowing paper lanterns hanging from ancient oak branches, cozy hygge mood, {FIXED_STYLE_BLOCK}"
        })

        # 3. Props: Key objects from all 5 vocabulary words and story actions
        prop_words = [
            (v.get("word") or "").strip()
            for v in self.vocab
            if isinstance(v, dict) and (v.get("word") or "").strip()
        ]
        if not prop_words:
            prop_words = ["蔬菜", "大树", "热气火锅", "木篮子", "小红花"]

        for p_idx, p_word in enumerate(prop_words, 1):
            clean_prop_tag = re.sub(r"[^\w\u4e00-\u9fa5]", "", p_word) or f"Item{p_idx}"
            elements.append({
                "category": "Props",
                "tag": f"[Element-Prop-{clean_prop_tag}]",
                "prompt": f"Storybook prop illustration of '{p_word}', charming hand-drawn details, isolated cleanly against soft pastel paper background, {FIXED_STYLE_BLOCK}"
            })

        return elements

    def _build_dynamic_tab1_scenes(self) -> List[Dict[str, str]]:
        """Dynamically constructs Tab 1 prompts: Cover, Scenes 1..N (N=8..10), Vocab 1..5, Outro."""
        scenes = []

        # 1. Cover Prompt: 100% Zero-Text Cover image with pure watercolor paper background and 4-legged anatomy keywords
        clean_title = re.sub(r"[《》\s]", "", str(self.title or "吃菜的大狼")) or "吃菜的大狼"
        cover_prompt = self.build_cover_prompt(clean_title)
        protagonist = self.char_manifest.get_protagonist() if hasattr(self, "char_manifest") and self.char_manifest else None
        if protagonist and protagonist.consistency_prompt_anchor not in cover_prompt:
            cover_prompt = CharacterConsistencyEngine.inject_character_anchors(cover_prompt, [protagonist])
        scenes.append({
            "scene": "Cover",
            "tag": f"[Scene-Cover-{clean_title}]",
            "prompt": cover_prompt
        })

        # 2. Dynamic Scene Prompts (Scenes 1..N where N=8..10)
        scene_groups: Dict[int, List[Dict[str, Any]]] = {}
        curr_scene = 1
        for line in self.lines:
            if not isinstance(line, dict):
                continue
            raw_s = line.get("scene_num")
            if raw_s is not None:
                try:
                    curr_scene = int(raw_s)
                except (ValueError, TypeError):
                    pass
            s_num = curr_scene
            if s_num not in scene_groups:
                scene_groups[s_num] = []
            scene_groups[s_num].append(line)

        if not scene_groups:
            for s_num, def_desc in DEFAULT_NARRATIVE_SCENES:
                sb_scene = None
                if hasattr(self, "storyboard_manifest") and self.storyboard_manifest:
                    for sc in self.storyboard_manifest.scenes:
                        if sc.scene_num == s_num:
                            sb_scene = sc
                            break
                if sb_scene and hasattr(self, "char_manifest") and self.char_manifest:
                    prompt_str = CharacterConsistencyEngine.synthesize_scene_prompt(sb_scene, def_desc, self.char_manifest)
                else:
                    prompt_str = self.build_scene_prompt(s_num, def_desc)
                scenes.append({
                    "scene": f"Scene {s_num}",
                    "tag": f"[Scene-{s_num}]",
                    "prompt": prompt_str
                })
        else:
            for s_num in sorted(scene_groups.keys()):
                lines_in_sc = scene_groups[s_num]
                en_descriptions = [
                    str(l.get("en", "")).strip()
                    for l in lines_in_sc
                    if isinstance(l, dict) and l.get("en")
                ]
                raw_desc = " ".join(en_descriptions)
                clean_desc = sanitize_prompt_text(raw_desc or "")
                sb_scene = None
                if hasattr(self, "storyboard_manifest") and self.storyboard_manifest:
                    for sc in self.storyboard_manifest.scenes:
                        if sc.scene_num == s_num:
                            sb_scene = sc
                            break
                if sb_scene and hasattr(self, "char_manifest") and self.char_manifest:
                    prompt_str = CharacterConsistencyEngine.synthesize_scene_prompt(sb_scene, clean_desc, self.char_manifest)
                else:
                    prompt_str = self.build_scene_prompt(s_num, clean_desc)
                    if hasattr(self, "char_manifest") and self.char_manifest and self.char_manifest.characters:
                        prompt_str = CharacterConsistencyEngine.inject_character_anchors(prompt_str, [self.char_manifest.get_protagonist()])
                scenes.append({
                    "scene": f"Scene {s_num}",
                    "tag": f"[Scene-{s_num}]",
                    "prompt": prompt_str
                })

        # 3. Outro Loop Prompt (No separate vocab image prompts needed since Slide 11 is a 2-column card layout on story background)
        scenes.append({
            "scene": "Outro",
            "tag": "[Outro-Loop]",
            "prompt": self.build_outro_prompt()
        })

        return scenes
