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
                "element_name": f"[Element-Character-Wolf] Luoluo the Gentle Wolf",
                "prompt": f"A fluffy, gentle-eyed big grey wolf wearing a cozy knit apron, holding a fresh green cabbage with a warm innocent smile, standing on two legs like a friendly storybook character, lush forest clearing, {FIXED_STYLE_BLOCK}"
            },
            {
                "category": "Characters",
                "element_name": f"[Element-Character-Rabbit] Little Rabbit",
                "prompt": f"A tiny white bunny with big curious eyes and a pink nose, wearing tiny yellow overalls, looking relieved and happy, standing in mossy grass, {FIXED_STYLE_BLOCK}"
            },
            # Backgrounds
            {
                "category": "Background",
                "element_name": f"[Element-Background-Forest] Enchanted Forest Meadow",
                "prompt": f"A sun-dappled fairy tale forest clearing with ancient mossy trees, wildflowers, soft golden sunlight streaming through leaves, cozy woodland atmosphere, {FIXED_STYLE_BLOCK}"
            },
            {
                "category": "Background",
                "element_name": f"[Element-Background-Cabin] Wolf Vegetable Garden Cabin",
                "prompt": f"A quaint whimsical wooden cottage with neat rows of vibrant carrots, pumpkins, and cabbages, wooden picket fence, soft morning mist, {FIXED_STYLE_BLOCK}"
            },
            # Props
            {
                "category": "Props",
                "element_name": f"[Element-Prop-Hotpot] Steaming Vegetable Hotpot",
                "prompt": f"A rustic bubbling ceramic hotpot filled with colorful sliced carrots, mushrooms, tofu, and leafy greens, gentle warm steam rising, placed on a wooden tree-stump table, {FIXED_STYLE_BLOCK}"
            },
            {
                "category": "Props",
                "element_name": f"[Element-Prop-FallenTree] Fallen Forest Tree Trunk",
                "prompt": f"A large moss-covered fallen pine log resting across a woodland trail, wild mushrooms growing on bark, dappled sunlight, {FIXED_STYLE_BLOCK}"
            }
        ]

        # --- TAB 1: SCENES ---
        tab1_scenes = [
            {
                "scene": "Cover",
                "title": f"[Scene-Cover] Title Card: {self.title}",
                "prompt": f"A cute big grey wolf smiling warmly and holding up a large fresh carrot, beside a tiny cheerful rabbit, fairy tale woodland background with soft morning sunbeams, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 1",
                "title": "[Scene 1] Luoluo in His Vegetable Garden",
                "prompt": f"The friendly big grey wolf Luoluo watering fresh rows of plump orange carrots and crisp green cabbages outside his cottage, morning sunbeams, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 2",
                "title": "[Scene 2] Forest Animals Hiding in Fear",
                "prompt": f"A timid white rabbit and small squirrel peeking nervously from behind a hollow mossy tree, watching the big wolf walk by, dramatic soft shadows, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 3",
                "title": "[Scene 3] The Wolf Rescuing the Little Rabbit",
                "prompt": f"The strong grey wolf carefully lifting a heavy fallen tree trunk with both paws, rescuing a frightened little bunny trapped underneath, heroic and gentle expression, {FIXED_STYLE_BLOCK}"
            },
            {
                "scene": "Scene 4",
                "title": "[Scene 4] The Hotpot Feast with New Friends",
                "prompt": f"The big wolf, little rabbit, and squirrel joyfully sitting together around a rustic wooden table, sharing a delicious steaming pot of vegetable soup, cozy festive twilight, {FIXED_STYLE_BLOCK}"
            }
        ]

        # Vocab items visual prompts
        for idx, v in enumerate(self.vocab, 1):
            w = v.get("word", "")
            en = v.get("en", "")
            tab1_scenes.append({
                "scene": f"Vocabulary {idx}",
                "title": f"[Vocabulary-{idx}] {w} ({en})",
                "prompt": f"Educational storybook flashcard visual featuring '{w}' ({en}), centered iconic illustration with whimsical hand-painted details, soft pastel background, {FIXED_STYLE_BLOCK}"
            })

        # Outro loop prompt
        tab1_scenes.append({
            "scene": "Outro",
            "title": "[Outro-Loop] Vocabulary Review & Next Episode Teaser",
            "prompt": f"The cute wolf and rabbit waving cheerfully towards the viewer, sitting beside a wooden signboard with soft glowing fairytale lanterns, evening forest, {FIXED_STYLE_BLOCK}"
        })

        # --- COMBINED TEXT FORMAT (Tab 2 on top, Tab 1 below, 1 line each, blank line between) ---
        gdoc_blocks = []
        gdoc_blocks.append("【TAB 2: ELEMENTS (Characters, Background, Props)】\n")
        for item in tab2_elements:
            gdoc_blocks.append(f"{item['element_name']}: {item['prompt']}")

        gdoc_blocks.append("\n【TAB 1: SCENES & VOCABULARY】\n")
        for item in tab1_scenes:
            gdoc_blocks.append(f"{item['title']}: {item['prompt']}")

        formatted_gdoc_text = "\n\n".join(gdoc_blocks)

        return {
            "tab1_scenes": tab1_scenes,
            "tab2_elements": tab2_elements,
            "formatted_gdoc_text": formatted_gdoc_text,
            "fixed_style": FIXED_STYLE_BLOCK
        }
