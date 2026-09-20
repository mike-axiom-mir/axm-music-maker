# AXM Music Maker

AXM Music Maker is the **composition, performance and adaptive-music specialist** for AXM.

It should let AI and humans create music together while retaining editable musical structure instead of flattening every result into one opaque audio file.

## Purpose

Grow toward creation of:

- beats and rhythm
- melody and harmony
- chord progressions
- bass lines
- instrument parts
- song sections and arrangements
- stems
- motifs and variations
- adaptive game music
- transitions, tension states and intensity layers
- vocal performances
- NPC dialogue / voice-over arrangements
- human recordings and imported performances
- AI-assisted composition and sound shaping
- later increasingly deterministic/reusable composition from accumulated explicit musical atoms, patterns and rules

AI-first creation is allowed where it genuinely adds capability. The long-term direction is to retain more explicit reusable musical knowledge so repeated creation does not require blind regeneration.

## Human + AI principle

A human should be able to change what AI created.

An AI should be able to continue from what a human changed.

Neither should require regenerating the whole piece.

```text
note / beat / sample / voice line
              |
              v
       musical atom/event
              |
              v
    phrase / clip / performance
              |
              v
         section / stem
              |
              v
       arrangement / score
              |
              v
       adaptive music state
```

Voice may remain here initially because dialogue/vocals are timed performances inside arrangements. Split a dedicated voice repository only if the capability becomes large enough to justify a real independent boundary.

## Separation

- `axm-audio-fabric` supplies audio primitives, processing, playback and runtime sound machinery.
- `axm-music-maker` owns composition/performance intent and structured musical source state.
- `axm-sound-mixer` provides the approachable Lego-like arranging/mixing workspace over music, voice and SFX.

## Immediate proving target

Create one structured game-music piece with multiple editable stems and at least two runtime states, for example:

`exploration -> danger -> combat`

The transitions and musical source state must remain inspectable. Rendering a WAV alone is not enough.

See `START_HERE_NEXT.md` and `PROJECT.json`.
