# AXM Music Maker

AXM Music Maker is the **composition, performance and adaptive-music specialist** for AXM.

It lets AI and humans create music together while retaining editable musical structure instead of flattening every result into one opaque audio file.

## Current executable capability

The repository now contains a dependency-light Python core for `axm.music-project/v1`.

It currently supports:

- tempo, PPQ and meter;
- editable note events;
- editable voice-line performance events;
- explicit provenance on projects, clips and events;
- clips, stems, sections and named adaptive states;
- explicit transition triggers;
- immediate / beat / bar transition quantization;
- deterministic transition selection by priority then transition id;
- canonical JSON serialization and project hashing;
- validation of broken references and malformed musical state;
- transition receipts that record exactly which rule was selected and when it becomes effective.

The example at `examples/three_state_score.json` proves one editable score with:

`exploration -> danger -> combat`

The exploration motif is reused rather than regenerated, danger adds a pulse and an editable NPC line, and combat adds a stronger bass layer. The state changes are explicit project data, not hidden runtime inference.

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

AI-first creation is allowed where it genuinely adds capability. AI-created material must retain explicit provenance; repeating the same prompt does not make the result deterministic.

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

Voice remains here initially because dialogue/vocals are timed performances inside arrangements. Split a dedicated voice repository only if a real independent capability boundary appears.

## Separation

- `axm-audio-fabric` supplies audio primitives, processing, playback and runtime sound machinery.
- `axm-music-maker` owns composition/performance intent and structured musical source state.
- `axm-sound-mixer` provides the approachable Lego-like arranging/mixing workspace over music, voice and SFX.

Music Maker does **not** yet render finished music audio. The current proof establishes editable score state and adaptive transition behavior; Audio Fabric remains the intended render/playback substrate.

## Verification

Run:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions also validates the unit suite and an example transition receipt on every push and pull request.

Passing tests prove schema/reference integrity, canonical replayable state, and transition scheduling behavior. They do **not** prove musical quality, game feel, vocal quality, mix quality, or aesthetic acceptance.

See `START_HERE_NEXT.md` and `PROJECT.json` for the next bounded build direction.
