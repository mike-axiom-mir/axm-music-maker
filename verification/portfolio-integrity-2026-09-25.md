# Reject nonfinite canonical tempo

Date: 2026-09-25 UTC

Base commit: `6257e2763cac3e64822867ce325e844a0f03cfd3`

Status: experimental repair, not merged or promoted.

## Observed failure

validate_project accepted both NaN and positive infinity as tempo_bpm. The new negative test failed before the repair.

## Repair

Tempo must be positive and finite. Existing finite integer and fractional tempo values are preserved.

## Verification

Command: `PYTHONPATH=src:. python -m unittest discover -s tests -v`

23 tests passed.

Regression tests exercise invalid input and valid-state continuity. The full repository command above passed on the repaired working tree. No production-readiness, deployment, or CANON claim is made.
