# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Validation reports shared by terminal and graphical interfaces."""

from dataclasses import dataclass, field
from pathlib import Path
import json

from profilelab.loader import InvalidProfileError
from profilelab.engine_validator import is_complete_profile_tree
from profilelab.system_checks import find_profile_reference_issues, find_setting_id_issues
from profilelab.validator import (
    find_duplicate_profile_names,
    find_inheritance_cycles,
    find_missing_parents,
    profile_paths,
)


@dataclass
class ValidationIssue:
    kind: str
    message: str
    paths: list[Path] = field(default_factory=list)


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_user_folder(profile_folder: Path, resources: Path) -> ValidationReport:
    """Resolve external parents only when present in a real matching source tree."""
    report = validate_folder(profile_folder)
    if not any(issue.kind == 'missing_parent' for issue in report.issues):
        return report
    parents = set()
    roots = [resources / 'profiles', profile_folder.parent.parent / 'system']
    for root in roots:
        for path in root.rglob('*.json') if root.is_dir() else []:
            if root == roots[1] and (roots[0] / path.relative_to(root).parts[0]).exists():
                continue  # The engine never overwrites its pinned vendor bundles.
            try:
                data = json.loads(path.read_text(encoding='utf-8-sig'))
                if isinstance(data, dict) and isinstance(data.get('name'), str):
                    parents.add((data.get('type'), data['name']))
            except (OSError, ValueError):
                continue  # Never excuse a missing parent using unreadable data.
    unresolved = []
    for issue in report.issues:
        if issue.kind == 'missing_parent' and issue.paths:
            try:
                data = json.loads(issue.paths[0].read_text(encoding='utf-8-sig'))
                if (data.get('type'), data.get('inherits')) in parents:
                    continue
            except (OSError, ValueError, TypeError):
                pass
        unresolved.append(issue)
    report.issues = unresolved
    return report


def validate_folder(profile_folder: Path) -> ValidationReport:
    """Return validation results without printing or exiting."""
    if not profile_folder.is_dir():
        return ValidationReport([ValidationIssue(
            "folder", f"{profile_folder}: folder does not exist", [profile_folder]
        )])

    if not profile_paths(profile_folder):
        return ValidationReport([ValidationIssue(
            "folder", f"{profile_folder}: no JSON profile files found", [profile_folder]
        )])

    try:
        errors = find_missing_parents(profile_folder)
        duplicates = find_duplicate_profile_names(profile_folder)
        cycles = find_inheritance_cycles(profile_folder)
    except InvalidProfileError as error:
        return ValidationReport([ValidationIssue(
            "invalid_profile", f"{error.profile_path}: {error.reason}",
            [error.profile_path],
        )])

    issues = []
    for error in errors:
        issues.append(ValidationIssue(
            "missing_parent",
            f"{error['path']}: {error['profile']} is missing parent "
            f"{error['missing_parent']}",
            [Path(error["path"])],
        ))

    for duplicate in duplicates:
        paths = ", ".join(duplicate["paths"])
        issues.append(ValidationIssue(
            "duplicate_name",
            f"duplicate profile name '{duplicate['profile']}' appears in: {paths}",
            [Path(path) for path in duplicate["paths"]],
        ))

    for cycle in cycles:
        issues.append(ValidationIssue(
            "inheritance_cycle", f"inheritance cycle: {' -> '.join(cycle)}"
        ))

    if is_complete_profile_tree(profile_folder):
        for issue in find_setting_id_issues(profile_folder):
            issues.append(ValidationIssue(
                "setting_id", f"{issue['path']}: {issue['message']}", [issue["path"]]
            ))
        for issue in find_profile_reference_issues(profile_folder):
            issues.append(ValidationIssue(
                "system_profile", f"{issue['path']}: {issue['message']}", [issue["path"]]
            ))

    return ValidationReport(issues)
