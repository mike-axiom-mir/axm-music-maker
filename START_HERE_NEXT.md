# START HERE NEXT

The first structured-score milestone is now complete and verified.

## Preserve what exists

Do **not** rebuild the canonical music model from scratch.

`axm_music/project.py` already validates `axm.music-project/v1` with tempo/meter, note and voice-line events, clips, stems, sections, states, transitions and explicit provenance.

`axm_music/adaptive.py` already resolves explicit triggers into deterministic transition receipts with immediate / beat / bar quantization.

`examples/three_state_score.json` already proves an editable exploration -> danger -> combat score.

## Strongest next bounded gap

Connect structured score state to a render/playback contract without flattening the source model.

The next builder should add the smallest adapter that can turn one section/state into an explicit render plan suitable for `axm-audio-fabric`, while preserving:

- note/voice event ids;
- source provenance;
- stem identity;
- timing in canonical ticks;
- project hash;
- state/section identity.

Prefer a render **plan/contract** before adding a large synthesis engine here. Audio Fabric owns low-level sound generation and playback.

## After that

High-value growth directions include:

- reusable motif/pattern transformation rules;
- chord/harmony representation;
- human MIDI/audio import with provenance;
- editable voice takes and recording references;
- adaptive crossfades/stingers layered on top of explicit state transitions;
- AI proposal records that remain distinguishable from deterministic transformations;
- Sound Mixer export/import contract.

## Truth boundary

Canonical state and green transition tests prove structural correctness, not musical quality. Do not claim composition quality, vocal quality, mix quality or game feel without actual listening/acceptance evidence.
