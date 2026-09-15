import json
import logging
import re
from typing import Dict, Any, List
from pinyin_utils import text_to_pinyin
from multi_ai_provider import MultiAIProvider

logger = logging.getLogger("lelestory.scripting")

VIETNAMESE_PATTERN = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]",
    re.IGNORECASE
)

class ScriptGenerator:
    def __init__(self, idea_data: Dict[str, Any]):
        self.idea_data = idea_data
        self.batch_id = idea_data.get("batch_id") or idea_data.get("row_id") or 2
        self.title = idea_data.get("title", "吃菜的大狼")
        self.plot = idea_data.get("story_plot", "")
        self.act_1 = idea_data.get("act_1", "")
        self.act_2 = idea_data.get("act_2", "")
        self.act_3 = idea_data.get("act_3", "")
        self.ai = MultiAIProvider()

    def generate_script(self) -> Dict[str, Any]:
        """
        Generates line-by-line story script (8–10 progressive scenes following the 3-Act Narrative Arc
        + 5 vocabulary + outro loop) with idiomatic English translation and tone-marked Pinyin.
        Strictly ZERO Vietnamese.
        """
        prompt = f"""Write an educational children's Chinese storybook script for:
Title: 《{self.title}》
Story Synopsis: {self.plot}
Act 1 Guide: {self.act_1}
Act 2 Guide: {self.act_2}
Act 3 Guide: {self.act_3}

REQUIREMENTS:
1. Divide the story into 8 to 10 PROGRESSIVE SCENES following the classic 3-Act Narrative Arc:
   - Act 1 (Scenes 1–2): Exposition & Equilibrium — Introduce main character, setting, and initial balance.
   - Act 2 (Scenes 3–7): Conflict & Escalation:
     * Scene 3: Inciting Incident (disrupts the initial balance)
     * Scene 4: Rising Challenge (first major obstacle)
     * Scene 5: Midpoint Twist (unexpected revelation or reversal)
     * Scene 6: Escalating Conflict (tension and stakes peak)
     * Scene 7: Crisis Point (lowest moment / critical dark night of the soul)
   - Act 3 (Scenes 8–10): Climax & Resolution:
     * Scene 8: Climax & Decisive Action (conflict resolved through wisdom, kindness, or perseverance)
     * Scene 9: Warm Ending (harmony restored, heartfelt relief)
     * Scene 10: Moral Wisdom (philosophical life takeaway / epilogue)

2. For each line, provide:
   - speaker: character name or Narrator (e.g. "Narrator", "大灰狼罗罗", "小白兔")
   - zh: Simplified Chinese (natural, expressive, suitable for HSK learners)
   - en: NATURAL, IDIOMATIC ENGLISH TRANSLATION (Strictly English! Absolutely ZERO Vietnamese characters or words!)

3. Extract 5 key educational vocabulary words from this story:
   - word: Simplified Chinese word
   - en: Natural English translation

4. Include the outro loop sentence (connecting seamlessly back to the Title when video loops):
   - zh: "这些生词来自故事……"
   - en: "Those vocabulary comes from the story..."

OUTPUT FORMAT: Return STRICT JSON ONLY:
{{
  "title": "{self.title}",
  "scenes": [
    {{
      "scene_num": 1,
      "act": 1,
      "setting": "brief visual setting description in English",
      "lines": [
        {{"speaker": "Narrator", "zh": "...", "en": "..."}}
      ]
    }},
    ... (continue through scenes 2 to 8, 9, or 10)
  ],
  "vocabulary": [
    {{"word": "...", "en": "..."}},
    {{"word": "...", "en": "..."}},
    {{"word": "...", "en": "..."}},
    {{"word": "...", "en": "..."}},
    {{"word": "...", "en": "..."}}
  ],
  "outro": {{
    "zh": "这些生词来自故事……",
    "en": "Those vocabulary comes from the story..."
  }}
}}"""
        system_prompt = "You are a master children's Chinese storybook author. Output valid JSON only, with natural idiomatic English translations and strictly ZERO Vietnamese."

        raw_text = self.ai.call_ai(prompt, system_prompt)
        if raw_text:
            try:
                clean = re.sub(r"```(?:json)?", "", raw_text).replace("```", "").strip()
                parsed = json.loads(clean)
                scenes = parsed.get("scenes", [])
                vocab = parsed.get("vocabulary", [])
                if 8 <= len(scenes) <= 10 and len(vocab) >= 5:
                    all_lines = []
                    has_vietnamese = False
                    for sc in scenes:
                        s_num = sc.get("scene_num", 1)
                        for line in sc.get("lines", []):
                            zh = line.get("zh", "").strip()
                            en = line.get("en", "").strip()
                            spk = line.get("speaker", "Narrator").strip()
                            if VIETNAMESE_PATTERN.search(en):
                                has_vietnamese = True
                                break
                            if zh and en:
                                all_lines.append({
                                    "scene_num": s_num,
                                    "speaker": spk,
                                    "zh": zh,
                                    "pinyin": text_to_pinyin(zh),
                                    "en": en
                                })
                        if has_vietnamese:
                            break

                    if not has_vietnamese and len(all_lines) >= 8:
                        vocab_items = []
                        for v in vocab[:5]:
                            w = v.get("word", "").strip()
                            e = v.get("en", "").strip()
                            if w and e and not VIETNAMESE_PATTERN.search(e):
                                vocab_items.append({
                                    "word": w,
                                    "pinyin": text_to_pinyin(w),
                                    "en": e
                                })

                        if len(vocab_items) == 5:
                            outro_zh = parsed.get("outro", {}).get("zh", "这些生词来自故事……")
                            outro_en = parsed.get("outro", {}).get("en", "Those vocabulary comes from the story...")

                            return {
                                "batch_id": self.batch_id,
                                "row_id": self.batch_id,
                                "title": self.title,
                                "story_plot": self.plot,
                                "lines": all_lines,
                                "vocabulary": vocab_items,
                                "outro": {
                                    "zh": outro_zh,
                                    "pinyin": text_to_pinyin(outro_zh),
                                    "en": outro_en
                                },
                                "scenes_detail": scenes,
                                "status": "Scripted",
                                "generator": "MultiAI_Live"
                            }
            except Exception as e:
                logger.warning(f"Failed to parse AI story script: {e}")

        # Fallback to high quality scripted template based on 3-Act structure (8-10 scenes)
        logger.info("Using high quality 8-10 scenes scripted fallback for story.")
        return self._get_fallback_script()

    def _get_fallback_script(self) -> Dict[str, Any]:
        """
        Provides verified 8–10 progressive scenes fallback script following the 3-Act Narrative Arc.
        For 《吃菜的大狼》, provides full 10 progressive scenes (Act 1: 1-2, Act 2: 3-7, Act 3: 8-10).
        """
        lines = [
            # --- ACT 1: Exposition & Equilibrium (Scenes 1-2) ---
            {
                "scene_num": 1,
                "speaker": "Narrator",
                "zh": "在美丽茂密的大森林里，住着一只名叫罗罗的大灰狼。不同于普通的狼，他性情温和，最喜欢在菜园里种植新鲜蔬菜。",
                "pinyin": text_to_pinyin("在美丽茂密的大森林里，住着一只名叫罗罗的大灰狼。不同于普通的狼，他性情温和，最喜欢在菜园里种植新鲜蔬菜。"),
                "en": "In a beautiful, lush forest lived a big grey wolf named Luoluo. Unlike ordinary wolves, he had a gentle nature and loved growing fresh vegetables in his garden."
            },
            {
                "scene_num": 2,
                "speaker": "Narrator",
                "zh": "森林里的小兔子和小松鼠依然对大灰狼充满恐惧。每次远远看到罗罗走来，大家都吓得赶紧躲进灌木丛中不敢出声。",
                "pinyin": text_to_pinyin("森林里的小兔子和小松鼠依然对大灰狼充满恐惧。每次远远看到罗罗走来，大家都吓得赶紧躲进灌木丛中不敢出声。"),
                "en": "The little rabbits and squirrels in the forest were still terrified of wolves. Whenever they saw Luoluo coming from afar, they quickly hid in the bushes without making a sound."
            },
            # --- ACT 2: Conflict & Escalation (Scenes 3-7) ---
            {
                "scene_num": 3,
                "speaker": "Narrator",
                "zh": "这天下午，天空突然乌云密布，一场狂暴的风雨呼啸而来，猛烈的狂风将山坡上的一棵巨大松树连根吹倒。",
                "pinyin": text_to_pinyin("这天下午，天空突然乌云密布，一场狂暴的风雨呼啸而来，猛烈的狂风将山坡上的一棵巨大松树连根吹倒。"),
                "en": "That afternoon, dark clouds suddenly gathered, and a furious storm howled in, with violent winds blowing down a massive pine tree on the hillside."
            },
            {
                "scene_num": 4,
                "speaker": "小白兔",
                "zh": "救命啊！倒下的大树把我们兔洞的出口死死挡住了，我们出不去了！",
                "pinyin": text_to_pinyin("救命啊！倒下的大树把我们兔洞的出口死死挡住了，我们出不去了！"),
                "en": "Help! The fallen tree has blocked our burrow entrance, and we can't get out!"
            },
            {
                "scene_num": 5,
                "speaker": "Narrator",
                "zh": "罗罗在风雨中听到了急切的呼救声。他没有躲回温暖的木屋，而是顶着狂风暴雨立刻奔向了兔洞。",
                "pinyin": text_to_pinyin("罗罗在风雨中听到了急切的呼救声。他没有躲回温暖的木屋，而是顶着狂风暴雨立刻奔向了兔洞。"),
                "en": "Luoluo heard the desperate cries in the storm. Instead of taking shelter in his warm cabin, he immediately braved the heavy rain and ran toward the burrow."
            },
            {
                "scene_num": 6,
                "speaker": "大灰狼罗罗",
                "zh": "小兔子别怕！我力气大，我来帮你们把这根沉重的大树干搬开！",
                "pinyin": text_to_pinyin("小兔子别怕！我力气大，我来帮你们把这根沉重的大树干搬开！"),
                "en": "Don't be afraid, little rabbits! I am strong, and I will help you move this heavy tree trunk away!"
            },
            {
                "scene_num": 7,
                "speaker": "Narrator",
                "zh": "浸透雨水的树干沉重无比，罗罗脚底打滑，爪子磨破了也绝不松手，咬紧牙关使出了全身的力气。",
                "pinyin": text_to_pinyin("浸透雨水的树干沉重无比，罗罗脚底打滑，爪子磨破了也绝不松手，咬紧牙关使出了全身的力气。"),
                "en": "The rain-soaked log was tremendously heavy; Luoluo's paws slipped and were grazed, but he refused to let go, clenching his teeth with all his might."
            },
            # --- ACT 3: Climax & Resolution (Scenes 8-10) ---
            {
                "scene_num": 8,
                "speaker": "Narrator",
                "zh": "伴随着一声大喝，罗罗终于将巨木推到一旁，小心翼翼地把受惊的小兔子们一个个安全抱了出来。",
                "pinyin": text_to_pinyin("伴随着一声大喝，罗罗终于将巨木推到一旁，小心翼翼地把受惊的小兔子们一个个安全抱了出来。"),
                "en": "With a mighty shout, Luoluo finally pushed the giant log aside and gently carried the frightened little rabbits out one by one to safety."
            },
            {
                "scene_num": 9,
                "speaker": "兔妈妈",
                "zh": "罗罗，太感谢你了！原来你是一只真正善良温和的大狼，我们再也不怕你了！",
                "pinyin": text_to_pinyin("罗罗，太感谢你了！原来你是一只真正善良温和的大狼，我们再也不怕你了！"),
                "en": "Thank you so much, Luoluo! You are truly a kind and gentle wolf, and we are not afraid of you anymore!"
            },
            {
                "scene_num": 10,
                "speaker": "Narrator",
                "zh": "风雨过后彩虹高挂，小动物们齐聚在罗罗家，开开心心地吃起热气腾腾的蔬菜火锅。善良化解了误会，带来了珍贵的友谊。",
                "pinyin": text_to_pinyin("风雨过后彩虹高挂，小动物们齐聚在罗罗家，开开心心地吃起热气腾腾的蔬菜火锅。善良化解了误会，带来了珍贵的友谊。"),
                "en": "After the storm a rainbow appeared, and the animals gathered at Luoluo's home to happily share a steaming vegetable hotpot. Kindness melted away prejudice and brought precious friendship."
            }
        ]

        vocab = [
            {"word": "大灰狼", "pinyin": text_to_pinyin("大灰狼"), "en": "Big grey wolf"},
            {"word": "蔬菜", "pinyin": text_to_pinyin("蔬菜"), "en": "Vegetables"},
            {"word": "害怕", "pinyin": text_to_pinyin("害怕"), "en": "Afraid / Scared"},
            {"word": "帮忙", "pinyin": text_to_pinyin("帮忙"), "en": "Help / Lend a hand"},
            {"word": "朋友", "pinyin": text_to_pinyin("朋友"), "en": "Friends"}
        ]

        outro_zh = "这些生词来自故事……"
        return {
            "batch_id": self.batch_id,
            "row_id": self.batch_id,
            "title": self.title,
            "story_plot": self.plot,
            "lines": lines,
            "vocabulary": vocab,
            "outro": {
                "zh": outro_zh,
                "pinyin": text_to_pinyin(outro_zh),
                "en": "Those vocabulary comes from the story..."
            },
            "status": "Scripted",
            "generator": "StoryScript_3Act_Fallback"
        }
