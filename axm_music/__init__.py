"""AXM Music Maker canonical structured-music core."""

from .adaptive import resolve_transition
from .project import ProjectValidationError, canonical_json, project_hash, validate_project
from .render_plan import RENDER_PLAN_SCHEMA, build_render_plan

__all__ = [
    "ProjectValidationError",
    "RENDER_PLAN_SCHEMA",
    "build_render_plan",
    "canonical_json",
    "project_hash",
    "resolve_transition",
    "validate_project",
]
