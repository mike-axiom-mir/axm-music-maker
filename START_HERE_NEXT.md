# START HERE NEXT

Continue this repository as structured music and performance authoring.

## First build

Create a canonical project model for:
- tempo / meter;
- musical events;
- clips / phrases;
- stems;
- sections;
- arrangement;
- adaptive game states;
- transitions.

Build one small proof with at least:
- exploration stem set;
- danger variation;
- combat variation;
- inspectable transition rules.

The structure must stay editable after generation.

## AI and deterministic growth

AI may propose melodies, arrangements, voices, lyrics or timbres. Preserve those proposals as explicit source/provenance.

As reusable musical atoms, patterns, transformations and rules accumulate, prefer deterministic/replayable reuse where it is actually sufficient. Do not call AI output deterministic merely because the same prompt was used twice.

## Voice

Keep vocals and NPC voice-over here initially as timed performances. Human recordings must be first-class inputs. Voice cloning or identity-sensitive synthesis must remain consent/provenance aware.

## Integration

Use Audio Fabric for low-level synthesis/render/playback. Export stems/performances for Sound Mixer rather than building a second mixer.
