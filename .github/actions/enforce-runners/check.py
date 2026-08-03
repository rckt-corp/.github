#!/usr/bin/env python3
"""Fail if any workflow job uses a runner outside the rckt allowlist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required (pip install pyyaml)\n")
    sys.exit(2)

WORKFLOW_GLOBS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
)

# Scale-set names / labels that identify rckt runners.
ALLOWED_MARKERS = frozenset(
    {
        "rckt-arc",
        "rckt-arc-lite",
        "native-macos",
    }
)

# Labels that may appear alongside allowed markers (macOS fleet, ARC defaults).
ALLOWED_EXTRA = frozenset(
    {
        "self-hosted",
        "Linux",
        "linux",
        "X64",
        "x64",
        "ARM64",
        "arm64",
        "macOS",
        "macos",
        "mac-mini",
        "xcode",
    }
)

GITHUB_HOSTED = re.compile(r"^(ubuntu|windows|macos)-", re.IGNORECASE)
EXPRESSION = re.compile(r"\$\{\{")


def workflow_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in WORKFLOW_GLOBS:
        files.extend(sorted(root.glob(pattern)))
    return files


def as_label_list(runs_on: object) -> list[str] | None:
    """Normalize runs-on to a label list, or None if unresolved/unsupported."""
    if isinstance(runs_on, str):
        return [runs_on]
    if isinstance(runs_on, list):
        if all(isinstance(x, str) for x in runs_on):
            return list(runs_on)
        return None
    if isinstance(runs_on, dict):
        labels = runs_on.get("labels")
        if labels is None:
            # Group-only targeting is not part of the rckt allowlist.
            return None
        if isinstance(labels, str):
            return [labels]
        if isinstance(labels, list) and all(isinstance(x, str) for x in labels):
            return list(labels)
        return None
    return None


def is_allowed(labels: list[str]) -> tuple[bool, str]:
    if not labels:
        return False, "empty runs-on"
    if any(EXPRESSION.search(label) for label in labels):
        return (
            False,
            "expression in runs-on (pin a concrete rckt runner label, or expand matrix to static values)",
        )
    hosted = [label for label in labels if GITHUB_HOSTED.match(label)]
    if hosted:
        return False, f"GitHub-hosted label(s): {', '.join(hosted)}"

    markers = [label for label in labels if label in ALLOWED_MARKERS]
    if not markers:
        return (
            False,
            "missing required marker (need one of: rckt-arc, rckt-arc-lite, native-macos)",
        )

    unknown = [
        label
        for label in labels
        if label not in ALLOWED_MARKERS and label not in ALLOWED_EXTRA
    ]
    if unknown:
        return False, f"unknown label(s): {', '.join(unknown)}"
    return True, "ok"


def iter_jobs(doc: object) -> list[tuple[str, dict]]:
    if not isinstance(doc, dict):
        return []
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return []
    out: list[tuple[str, dict]] = []
    for name, job in jobs.items():
        if isinstance(job, dict):
            out.append((str(name), job))
    return out


def matrix_runner_candidates(job: dict, expr: str) -> list[list[str]] | None:
    """Best-effort: resolve runs-on: ${{ matrix.X }} from a static matrix map."""
    match = re.search(r"matrix\.([A-Za-z_][A-Za-z0-9_]*)", expr)
    if not match:
        return None
    key = match.group(1)
    strategy = job.get("strategy")
    if not isinstance(strategy, dict):
        return None
    matrix = strategy.get("matrix")
    if not isinstance(matrix, dict):
        return None
    values = matrix.get(key)
    if not isinstance(values, list) or not values:
        return None

    candidates: list[list[str]] = []
    for value in values:
        labels = as_label_list(value)
        if labels is None:
            return None
        candidates.append(labels)
    return candidates


def check_job(path: Path, job_name: str, job: dict) -> list[str]:
    errors: list[str] = []
    if "runs-on" not in job:
        # Reusable workflow call jobs have no runs-on; runner policy applies in the callee.
        if "uses" in job:
            return []
        errors.append(f"{path}:{job_name}: missing runs-on")
        return errors

    runs_on = job["runs-on"]
    if isinstance(runs_on, str) and EXPRESSION.search(runs_on):
        candidates = matrix_runner_candidates(job, runs_on)
        if not candidates:
            errors.append(
                f"{path}:{job_name}: unresolved runs-on expression {runs_on!r}"
            )
            return errors
        for labels in candidates:
            ok, reason = is_allowed(labels)
            if not ok:
                errors.append(
                    f"{path}:{job_name}: matrix runs-on {labels!r} not allowed ({reason})"
                )
        return errors

    labels = as_label_list(runs_on)
    if labels is None:
        errors.append(f"{path}:{job_name}: unsupported runs-on form: {runs_on!r}")
        return errors

    ok, reason = is_allowed(labels)
    if not ok:
        errors.append(f"{path}:{job_name}: runs-on {labels!r} not allowed ({reason})")
    return errors


def check_file(path: Path) -> list[str]:
    try:
        docs = list(yaml.safe_load_all(path.read_text()))
    except yaml.YAMLError as exc:
        return [f"{path}: YAML parse error: {exc}"]

    errors: list[str] = []
    for doc in docs:
        for job_name, job in iter_jobs(doc):
            errors.extend(check_job(path, job_name, job))
    return errors


def main() -> int:
    root = Path(".").resolve()
    files = workflow_files(root)
    if not files:
        print("No workflow files under .github/workflows; nothing to check.")
        return 0

    errors: list[str] = []
    for path in files:
        errors.extend(check_file(path))

    if errors:
        print("Disallowed GitHub Actions runners detected:\n", file=sys.stderr)
        for error in errors:
            print(f"::error::{error}", file=sys.stderr)
            print(f"  - {error}", file=sys.stderr)
        print(
            "\nUse one of: rckt-arc, rckt-arc-lite, or native-macos "
            "(optionally with approved extra labels).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: checked {len(files)} workflow file(s); all runs-on values are allowed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
