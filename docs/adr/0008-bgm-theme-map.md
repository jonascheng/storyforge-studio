---
status: accepted
---

# BGM Theme Map and Lazy Generation

BGM generation per scene created disconnected audio that didn't feel like a cohesive movie score. We've introduced a `bgm_map.json` to define a story's BGM themes (e.g., tension, daily) upfront, and scenes now reference a `theme_id` instead of defining their own unique prompts.

The AI Director scans the source text *before* script breakdown to define a constrained set of themes. During audio mixing, BGM generation is lazy: if a theme's audio file doesn't exist yet, it's generated via Lyria; otherwise, the existing audio is reused. This enforces "theme song" consistency across scenes and reduces unnecessary Lyria API calls, while allowing users to manage BGM via a centralized map.
