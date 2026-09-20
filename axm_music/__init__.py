"""AXM Music Maker canonical structured-music core."""

from .adaptive import resolve_transition
from .project import ProjectValidationError, canonical_json, project_hash, validate_project

__all__ = [
    "ProjectValidationError",
    "canonical_json",
    "project_hash",
    "resolve_transition",
    "validate_project",
]
