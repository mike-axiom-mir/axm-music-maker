import json
import unittest
from pathlib import Path

from axm_music import ProjectValidationError, build_render_plan, project_hash


ROOT = Path(__file__).resolve().parents[1]


def load_example():
    return json.loads((ROOT / "examples" / "three_state_score.json").read_text(encoding="utf-8"))


class RenderPlanTests(unittest.TestCase):
    def test_danger_state_preserves_source_identity_and_ticks(self):
        project = load_example()
        plan = build_render_plan(project, "danger")

        self.assertEqual(plan["schema"], "axm.music-audio-render-plan/v1")
        self.assertEqual(plan["target"], "axm-audio-fabric")
        self.assertEqual(plan["project_id"], project["id"])
        self.assertEqual(plan["project_sha256"], project_hash(project))
        self.assertEqual(plan["state_id"], "danger")
        self.assertEqual(plan["section_id"], "danger-section")
        self.assertEqual(plan["section_length_ticks"], 15360)

        stems = {stem["stem_id"]: stem for stem in plan["stems"]}
        self.assertEqual(set(stems), {"motif", "danger-rhythm", "danger-dialogue"})

        motif_event = stems["motif"]["events"][0]
        self.assertEqual(motif_event["event_id"], "m1")
        self.assertEqual(motif_event["clip_id"], "motif-a")
        self.assertEqual(motif_event["start_tick"], 0)
        self.assertEqual(motif_event["duration_ticks"], 720)
        self.assertEqual(motif_event["payload"], {"pitch_midi": 57, "velocity": 72})
        self.assertEqual(motif_event["realization"]["kind"], "instrument")
        self.assertEqual(motif_event["realization"]["binding_key"], "motif")

    def test_voice_line_stays_editable_and_provenance_is_preserved(self):
        plan = build_render_plan(load_example(), "danger")
        voice_stem = next(stem for stem in plan["stems"] if stem["stem_id"] == "danger-dialogue")
        voice = voice_stem["events"][0]

        self.assertEqual(voice["event_id"], "v1")
        self.assertEqual(voice["payload"]["speaker_id"], "npc-guide")
        self.assertEqual(voice["payload"]["text"], "Movement ahead.")
        self.assertEqual(voice["provenance"], {"origin": "human", "source_id": "seed-dialogue"})
        self.assertEqual(voice["realization"]["kind"], "voice_performance")
        self.assertEqual(voice["realization"]["binding_key"], "v1")

    def test_ai_provenance_is_not_rewritten_by_adapter(self):
        project = load_example()
        project["clips"][0]["events"][0]["provenance"] = {
            "origin": "ai",
            "source_id": "proposal-77",
            "model_ref": "external-composer",
        }
        plan = build_render_plan(project, "exploration")
        provenance = plan["stems"][0]["events"][0]["provenance"]
        self.assertEqual(provenance["origin"], "ai")
        self.assertEqual(provenance["source_id"], "proposal-77")
        self.assertEqual(provenance["model_ref"], "external-composer")

    def test_plan_is_deterministic_for_same_project_and_state(self):
        project = load_example()
        self.assertEqual(build_render_plan(project, "combat"), build_render_plan(project, "combat"))

    def test_adapter_does_not_silently_loop_short_clips(self):
        plan = build_render_plan(load_example(), "exploration")
        stem = plan["stems"][0]
        self.assertEqual(stem["playback_policy"], "once_at_section_start")
        self.assertEqual(stem["clip_length_ticks"], 3840)
        self.assertEqual(stem["uncovered_tail_ticks"], 11520)
        self.assertFalse(plan["truth_boundary"]["looping_inferred"])
        self.assertFalse(plan["truth_boundary"]["audio_rendered"])

    def test_multiple_clips_are_rejected_until_placement_is_explicit(self):
        project = load_example()
        project["stems"][0]["clip_ids"].append("danger-pulse")
        with self.assertRaisesRegex(ProjectValidationError, "placement/loop semantics are not canonical"):
            build_render_plan(project, "exploration")

    def test_unknown_state_is_rejected(self):
        with self.assertRaisesRegex(ProjectValidationError, "unknown state"):
            build_render_plan(load_example(), "missing")


if __name__ == "__main__":
    unittest.main()
