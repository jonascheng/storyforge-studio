---
status: accepted
---

# Scene Ambience and Three-layer Audio Mixing

To make audiobooks more immersive, we introduce "Scene Ambience" — continuous ambient sounds (such as rain, wind, fireplace, forest, night, and indoor room) that play underneath dialogue and background music.

## 1. Domain Modeling and Entities
- `Scene` entity is extended with `ambience_id: str | None = None`.
- The AI Director automatically assigns an `ambience_id` to each scene from a built-in `AmbienceCatalog` based on scene setting and mood.
- No dynamic per-story user map or external API generation is required; ambience assets are bundled lightweight CC0 audio loops (<600 KB total), requiring zero external dependencies, zero network requests, and zero API costs.

## 2. Three-layer Audio Mixing Hierarchy
Audio in each scene follows a structured three-layer sandwich hierarchy:
1. **Dialogue & Narration (Top layer, 0 dBFS)**: The characters and narrator remain the dominant, crystal-clear focus.
2. **Scene BGM (Middle layer, -18 dBFS)**: Emotional score with 2s fade-in/fade-out, crossfade looped.
3. **Scene Ambience (Bottom layer)**:
   - When both BGM and Ambience are active: Ambience is attenuated to **-22 dBFS** (4 dB below BGM to prevent auditory clutter).
   - When Ambience is active without BGM: Ambience plays at **-18 dBFS**.
   - Timing & Loop: 2s fade-in and 2s fade-out, 1s crossfade looping to match dialogue duration exactly.
