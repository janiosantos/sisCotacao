#!/usr/bin/env python3
"""Resolve versoes e candidatas sem aceitar tags digitadas no deploy."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from typing import Iterable


FINAL_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
RC_TAG_RE = re.compile(r"^(v(\d+)\.(\d+)\.(\d+))-rc\.(\d+)\.(\d+)$")


class ReleaseControlError(ValueError):
    """Indica estado de release ambiguo ou incompleto."""


@dataclass(frozen=True)
class ReleaseCandidate:
    tag: str
    version_tag: str
    version: tuple[int, int, int]
    run_id: int
    run_attempt: int


def _git_tags() -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [tag.strip() for tag in result.stdout.splitlines() if tag.strip()]


def _final_versions(tags: Iterable[str]) -> dict[str, tuple[int, int, int]]:
    versions: dict[str, tuple[int, int, int]] = {}
    for tag in tags:
        match = FINAL_TAG_RE.fullmatch(tag)
        if match:
            versions[tag] = tuple(int(part) for part in match.groups())
    return versions


def _release_candidates(tags: Iterable[str]) -> list[ReleaseCandidate]:
    candidates: list[ReleaseCandidate] = []
    for tag in tags:
        match = RC_TAG_RE.fullmatch(tag)
        if not match:
            continue
        candidates.append(
            ReleaseCandidate(
                tag=tag,
                version_tag=match.group(1),
                version=tuple(int(match.group(index)) for index in (2, 3, 4)),
                run_id=int(match.group(5)),
                run_attempt=int(match.group(6)),
            )
        )
    return candidates


def next_version(tags: Iterable[str], bump: str) -> str:
    """Calcula a proxima versao e impede dois ciclos concorrentes."""
    all_tags = list(tags)
    finals = _final_versions(all_tags)
    if not finals:
        raise ReleaseControlError(
            "nenhuma tag final vMAJOR.MINOR.PATCH encontrada; regularize o baseline"
        )

    major, minor, patch = max(finals.values())
    if bump == "major":
        next_parts = (major + 1, 0, 0)
    elif bump == "minor":
        next_parts = (major, minor + 1, 0)
    elif bump == "patch":
        next_parts = (major, minor, patch + 1)
    else:
        raise ReleaseControlError(f"incremento invalido: {bump}")

    result = f"v{next_parts[0]}.{next_parts[1]}.{next_parts[2]}"
    pending_versions = {
        candidate.version_tag
        for candidate in _release_candidates(all_tags)
        if candidate.version_tag not in finals
    }
    other_pending = sorted(pending_versions - {result})
    if other_pending:
        raise ReleaseControlError(
            "ja existe outro ciclo candidato nao publicado: " + ", ".join(other_pending)
        )
    return result


def latest_candidate(tags: Iterable[str]) -> str:
    """Seleciona a tentativa mais recente do unico ciclo ainda publicavel."""
    all_tags = list(tags)
    finals = _final_versions(all_tags)
    pending = [
        candidate
        for candidate in _release_candidates(all_tags)
        if candidate.version_tag not in finals
    ]
    if not pending:
        raise ReleaseControlError(
            "nenhuma release candidate pendente; execute o staging completo"
        )

    pending_versions = {candidate.version_tag for candidate in pending}
    if len(pending_versions) != 1:
        raise ReleaseControlError(
            "mais de um ciclo candidato pendente: " + ", ".join(sorted(pending_versions))
        )
    return max(pending, key=lambda candidate: (candidate.run_id, candidate.run_attempt)).tag


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="calcula a proxima versao final")
    next_parser.add_argument("--bump", choices=("patch", "minor", "major"), required=True)
    subparsers.add_parser("candidate", help="seleciona a candidata pendente mais recente")

    args = parser.parse_args()
    try:
        if args.command == "next":
            print(next_version(_git_tags(), args.bump))
        else:
            print(latest_candidate(_git_tags()))
    except (ReleaseControlError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
