---
status: accepted
---

# Procedural Foley SFX Synthesis

To make StoryForge audiobooks dynamic with transient action sounds (such as door creaks, footsteps, whooshes, thumps, heartbeat, thunder), we introduce procedural Foley SFX synthesis inspired by `lemomo-ai/lemo-opuscar`.

## 1. Domain Modeling and Entities
- `FoleyCue`: Represents a discrete transient action sound effect cue with `sfx_id`, `timestamp_ms`, and `volume`.
- `FoleyDefinition`: Metadata for built-in Foley sounds including ID, Chinese display name, description, typical duration, and keywords.
- `FoleySynthesizer`: Infrastructure DSP synthesizer generating high-fidelity mono audio waveforms using pure mathematics (`numpy` & `scipy.signal`), converted into `pydub.AudioSegment`.

## 2. Zero-Download Procedural DSP Architecture
- Rather than downloading or bundling heavy sound libraries, all action sound effects are generated algorithmically on demand.
- Primitives include bandpass/lowpass/highpass Butterworth filters, exponential envelopes, Brownian noise, and harmonic summation.
- Supported core sounds:
  1. `creak` (開門吱呀聲)
  2. `step` (腳步聲)
  3. `whoosh` (呼嘯掠過聲)
  4. `thump` (重擊悶響聲)
  5. `crash` (碎裂撞擊聲)
  6. `heartbeat` (心跳咚咚聲)
  7. `rumble` (低鳴雷聲)
  8. `click` (機械扣合聲)
  9. `ding` (清脆鈴鐺聲)
  10. `ignite` (火焰燃起聲)
- Advantages: Zero external asset download, zero storage overhead, zero network dependency, deterministic, and instant generation.

## 3. Audio Ducking and Four-layer Mixing Hierarchy
- When transient Foley cues occur, background score (BGM) is dynamically ducked:
  - Attack: 60 ms smooth attenuation curve.
  - Hold: Sustained attenuation at -8 dBFS (or user-configured `duck_db`).
  - Release: 300 ms quadratic curve smooth recovery.
- Mixing hierarchy:
  1. Dialogue (0 dBFS, top)
  2. Foley SFX (0 dBFS / adjusted volume)
  3. BGM (-18 dBFS with automatic ducking on Foley events)
  4. Ambience (-22 dBFS / -18 dBFS without BGM)
