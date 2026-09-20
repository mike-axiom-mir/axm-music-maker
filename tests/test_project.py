import json
import unittest
from pathlib import Path

from axm_music import ProjectValidationError, project_hash, resolve_transition, validate_project


ROOT = Path(__file__).resolve().parents[1]


def load_example():
    return json.loads((ROOT / "examples" / "three_state_score.json").read_text(encoding="utf-8"))


class MusicProjectTests(unittest.TestCase):
    def test_example_is_valid_and_keeps_editable_structure(self):
        project = validate_project(load_example())
        self.assertEqual(project["initial_state"], "exploration")
        self.assertEqual({state["id"] for state in project["states"]}, {"exploration", "danger", "combat"})
        self.assertIn("motif-a", {clip["id"] for clip in project["clips"]})
        voice_events = [
            event
            for clip in project["clips"]
            for event in clip["events"]
            if event["kind"] == "voice_line"
        ]
        self.assertEqual(voice_events[0]["text"], "Movement ahead.")
        self.assertEqual(voice_events[0]["provenance"]["origin"], "human")

    def test_project_hash_is_independent_of_json_key_order(self):
        project = load_example()
        reordered = {key: project[key] for key in reversed(list(project.keys()))}
        self.assertEqual(project_hash(project), project_hash(reordered))

    def test_ai_proposal_provenance_is_not_silently_rewritten(self):
        project = load_example()
        event = project["clips"][0]["events"][0]
        event["provenance"] = {
            "origin": "ai",
            "source_id": "proposal-001",
            "model_ref": "external-composer-example"
        }
        validated = validate_project(project)
        kept = validated["clips"][0]["events"][0]["provenance"]
        self.assertEqual(kept["origin"], "ai")
        self.assertEqual(kept["source_id"], "proposal-001")
        self.assertEqual(kept["model_ref"], "external-composer-example")

    def test_bar_transition_quantizes_without_hidden_choice(self):
        receipt = resolve_transition(
            load_example(),
            current_state="exploration",
            trigger="threat",
            request_tick=1000,
        )
        self.assertEqual(receipt["transition_id"], "explore-to-danger")
        self.assertEqual(receipt["next_state"], "danger")
        self.assertEqual(receipt["effective_tick"], 3840)
        self.assertEqual(receipt["quantize"], "bar")

    def test_beat_transition_quantizes_to_next_beat(self):
        receipt = resolve_transition(
            load_example(),
            current_state="danger",
            trigger="engage",
            request_tick=3901,
        )
        self.assertEqual(receipt["next_state"], "combat")
        self.assertEqual(receipt["effective_tick"], 4800)

    def test_priority_makes_selection_deterministic(self):
        project = load_example()
        project["transitions"].append(
            {
                "id": "alternate-danger",
                "from_state": "exploration",
                "trigger": "threat",
                "to_state": "combat",
                "quantize": "immediate",
                "priority": 5
            }
        )
        receipt = resolve_transition(
            project,
            current_state="exploration",
            trigger="threat",
            request_tick=1,
        )
        self.assertEqual(receipt["transition_id"], "explore-to-danger")

    def test_no_transition_is_explicit(self):
        receipt = resolve_transition(
            load_example(),
            current_state="exploration",
            trigger="unknown-event",
            request_tick=123,
        )
        self.assertEqual(receipt["status"], "no_transition")
        self.assertEqual(receipt["next_state"], "exploration")
        self.assertIsNone(receipt["transition_id"])

    def test_broken_reference_is_rejected(self):
        project = load_example()
        project["sections"][0]["stem_ids"] = ["missing-stem"]
        with self.assertRaises(ProjectValidationError):
            validate_project(project)

    def test_validation_returns_copy_not_mutable_alias(self):
        original = load_example()
        validated = validate_project(original)
        validated["states"][0]["id"] = "changed"
        self.assertEqual(original["states"][0]["id"], "exploration")


if __name__ == "__main__":
    unittest.main()
