import logging
from typing import Dict, Any, List

logger = logging.getLogger("lelestory.scripting")

FIXED_STYLE_BLOCK = (
    "charming watercolor storybook illustration, whimsical children's book art style, "
    "hand-drawn aesthetic, soft textured paper background, warm soft pastel color palette, "
    "gentle sunlit fairytale lighting, cozy hygge mood, Studio Ghibli inspired warmth, "
    "vertical 9:16 composition, main subjects focused in upper and middle frame, "
    "clean uncluttered lower third for text overlay --ar 9:16 --stylize 250"
)

class PromptBuilder:
    def __init__(self, script_payload: Dict[str, Any]):
        self.batch_id = script_payload.get("batch_id", 2)
        self.title = script_payload.get("title", "吃菜的大狼")
        self.plot = script_payload.get("story_plot", "")
        self.lines = script_payload.get("lines", [])
        self.vocab = script_payload.get("vocabulary", [])
        self.outro = script_payload.get("outro", {})

    def build_prompts(self) -> Dict[str, Any]:
        """Builds Tab 1 (Scenes & Vocabulary) and Tab 2 (Elements: Characters, Backgrounds, Props) image prompts."""
        # --- TAB 2: ELEMENTS ---
        tab2_elements = [
            # Characters
            {
                "category": "Characters",
                "tag": "[Element-Character-Wolf]",
                "prompt": f"A fluffy, gentle-eyed big grey wolf wearing a cozy knit apron, holding a fresh green cabbage with a warm innocent smile, standing on two legs like a friendly storybook character, lush forest clearing, {FIXED_STYLE_BLOCK}"
            },
            {
                "category": "Characters",
                "tag": "[Element-Character-Rabbit]",
                "prompt": f"A tiny white bunny with big curious eyes and a pink nose, wearing tiny yellow overalls, looking relieved and happy, standing in mossy grass, {FIXED_STYLE_BLOCK}"
            },
            # Backgrounds
            {
                "category": "Background",
                "tag": "[Element-Background-Forest]",
                "prompt": f"A sun-dappled fairy tale forest clearing with ancient mossy trees, wildflowers, soft golden sunlight streaming through leaves, cozy woodland atmosphere, {FIXED_STYLE_BLOCK}"
            },
            {
                "category": "Background",
                "tag": "[Element-Background-Cabin]",
                "prompt": f"A quaint whimsical wooden cottage with neat rows of vibrant carrots, pumpkins, and cabbages, wooden picket fence, soft morning mist, {FIXED_STYLE_BLOCK}"
            },
            # Props
            {
                "category": "Props",
                "tag": "[Element-Prop-Hotpot]",
                "prompt": f"A rustic bubbling ceramic hotpot filled with colorful sliced carrots, mushrooms, tofu, and leafy greens, gentle warm steam rising, placed on a wooden tree-stump table, {FIXED_STYLE_BLOCK}"
            },
            {
                "category": "Props",
                "tag": "[Element-Prop-FallenTree]",
                "prompt": f"A large moss-covered fallen pine log resting across a woodland trail, wild mushrooms growing on bark, dappled sunlight, {FIXED_STYLE_BLOCK}"
            }
        ]

        # --- TAB 1: SCENES & VOCABULARY ---
        tab1_scenes = [
            {
                "scene": "Cover",
                "tag": f"[Scene-Cover-{self.title}]",
                "prompt": f"A cute big grey wolf smiling warmly and holding up a large fresh carrot, beside a tiny cheerful rabbit, fairy tale woodland background with soft morning sunbeams, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 1",
                "tag": "[Scene-1]",
                "prompt": f"The friendly big grey wolf Luoluo watering fresh rows of plump orange carrots and crisp green cabbages outside his cottage, morning sunbeams, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 2",
                "tag": "[Scene-2]",
                "prompt": f"A timid white rabbit and small squirrel peeking nervously from behind a hollow mossy tree, watching the big wolf walk by, dramatic soft shadows, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 3",
                "tag": "[Scene-3]",
                "prompt": f"The strong grey wolf carefully lifting a heavy fallen tree trunk with both paws, rescuing a frightened little bunny trapped underneath, heroic and gentle expression, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 4",
                "tag": "[Scene-4]",
                "prompt": f"The big wolf, little rabbit, and squirrel joyfully sitting together around a rustic wooden table, sharing a delicious steaming pot of vegetable soup, cozy festive twilight, {FIXED_STYLE_BLOCK}"
            }
        ]

        # Vocab items visual prompts
        for idx, v in enumerate(self.vocab, 1):
            w = v.get("word", "")
            en = v.get("en", "")
            tab1_scenes.append({
                "scene": f"Vocabulary {idx}",
                "tag": f"[Vocabulary-{idx}-{w}]",
                "prompt": f"Educational storybook flashcard visual featuring '{w}' ({en}), centered iconic illustration with whimsical hand-painted details, soft pastel background, {FIXED_STYLE_BLOCK}"
            })

        # Outro loop prompt
        tab1_scenes.append({
            "scene": "Outro",
            "tag": "[Outro-Loop]",
            "prompt": f"The cute wolf and rabbit waving cheerfully towards the viewer, sitting beside a wooden signboard with soft glowing fairytale lanterns, evening forest, {FIXED_STYLE_BLOCK}"
        })

        # --- STRICT 1-LINE PER PROMPT FORMAT: Tab 2 on top, Tab 1 below, 1 blank line between ---
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
            "fixed_style": FIXED_STYLE_BLOCK
        }
