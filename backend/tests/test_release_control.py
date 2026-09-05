from scripts.release_control import ReleaseControlError, latest_candidate, next_version


def test_next_version_uses_latest_final_semver_and_ignores_legacy_tags():
    tags = ["v1.6.4-estavel", "v2.39.1", "v2.40.0", "nao-semver"]

    assert next_version(tags, "patch") == "v2.40.1"
    assert next_version(tags, "minor") == "v2.41.0"
    assert next_version(tags, "major") == "v3.0.0"


def test_next_version_allows_new_attempt_for_same_pending_cycle():
    tags = ["v2.40.0", "v2.40.1-rc.100.1"]

    assert next_version(tags, "patch") == "v2.40.1"


def test_next_version_blocks_concurrent_release_cycles():
    tags = ["v2.40.0", "v2.40.1-rc.100.1"]

    try:
        next_version(tags, "minor")
    except ReleaseControlError as exc:
        assert "v2.40.1" in str(exc)
    else:
        raise AssertionError("ciclo concorrente deveria ser bloqueado")


def test_latest_candidate_selects_latest_run_and_attempt():
    tags = [
        "v2.40.0",
        "v2.40.1-rc.100.1",
        "v2.40.1-rc.101.1",
        "v2.40.1-rc.101.2",
    ]

    assert latest_candidate(tags) == "v2.40.1-rc.101.2"


def test_latest_candidate_ignores_already_published_cycle():
    tags = ["v2.40.0", "v2.40.0-rc.99.1", "v2.40.1-rc.101.1"]

    assert latest_candidate(tags) == "v2.40.1-rc.101.1"


def test_latest_candidate_rejects_ambiguous_cycles():
    tags = ["v2.40.0", "v2.40.1-rc.101.1", "v2.41.0-rc.102.1"]

    try:
        latest_candidate(tags)
    except ReleaseControlError as exc:
        assert "v2.40.1" in str(exc)
        assert "v2.41.0" in str(exc)
    else:
        raise AssertionError("candidatas ambiguas deveriam ser bloqueadas")
