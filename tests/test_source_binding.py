from __future__ import annotations

from copy import deepcopy

from cybercore.orchestration.source_binding import bind_provider_observations


def _github_observation(source_id="github-main", **locator_overrides):
    locator = {
        "repository": "cyberDJs/CyberCore",
        "ref": "main",
        "resource_kind": "file",
        "path": "PROJECT_STATE.md",
    }
    locator.update(locator_overrides)
    return {
        "source_id": source_id,
        "provider": "GITHUB",
        "locator": locator,
        "facts": {"pr:40:state": "merged"},
        "observed_at": "2026-08-19T13:24:03Z",
    }


def _github_binding(binding_id="github-main"):
    return {
        "binding_id": binding_id,
        "provider": "GITHUB",
        "authority": "CANONICAL",
        "match": {
            "repository": "cyberDJs/CyberCore",
            "ref": "main",
            "resource_kind": "file",
        },
    }


def test_exact_trusted_binding_assigns_authority_and_provenance():
    result = bind_provider_observations([_github_observation()], [_github_binding()])

    assert result["status"] == "BOUND"
    assert result["binding_issues"] == []
    assert result["sources"] == [
        {
            "source_id": "github-main",
            "authority": "CANONICAL",
            "facts": {"pr:40:state": "merged"},
        }
    ]
    assert result["provenance"][0]["binding_id"] == "github-main"
    assert result["provenance"][0]["provider"] == "GITHUB"


def test_unbound_observation_fails_closed():
    observation = _github_observation(repository="other/repo")
    result = bind_provider_observations([observation], [_github_binding()])

    assert result["status"] == "UNKNOWN"
    assert result["sources"] == []
    assert result["binding_issues"][0]["reason"] == "UNBOUND"


def test_ambiguous_binding_fails_closed_even_when_authority_matches():
    bindings = [_github_binding("a"), _github_binding("b")]
    result = bind_provider_observations([_github_observation()], bindings)

    assert result["status"] == "UNKNOWN"
    assert result["binding_issues"][0]["reason"] == "AMBIGUOUS_BINDING"
    assert result["binding_issues"][0]["candidate_binding_ids"] == ["a", "b"]


def test_provider_payload_cannot_self_declare_authority():
    observation = _github_observation()
    observation["facts"]["authority"] = "WORKING"
    result = bind_provider_observations([observation], [_github_binding()])

    assert result["status"] == "BOUND"
    assert result["sources"][0]["authority"] == "CANONICAL"


def test_newer_drive_observation_does_not_gain_canonical_authority():
    observation = {
        "source_id": "drive-working",
        "provider": "GOOGLE_DRIVE",
        "locator": {
            "file_id": "file-1",
            "ancestor_id": "working-folder",
            "resource_kind": "file",
            "mime_type": "text/plain",
        },
        "facts": {"pr:40:state": "open"},
        "observed_at": "2099-01-01T00:00:00Z",
    }
    binding = {
        "binding_id": "drive-working",
        "provider": "GOOGLE_DRIVE",
        "authority": "WORKING",
        "match": {"ancestor_id": "working-folder"},
    }

    result = bind_provider_observations([observation], [binding])

    assert result["status"] == "BOUND"
    assert result["sources"][0]["authority"] == "WORKING"


def test_provider_wide_binding_is_rejected():
    binding = {
        "binding_id": "too-broad",
        "provider": "GITHUB",
        "authority": "CANONICAL",
        "match": {},
    }
    result = bind_provider_observations([_github_observation()], [binding])

    assert result["status"] == "UNKNOWN"
    assert result["binding_issues"][0]["reason"] == "INVALID_BINDING"


def test_unsafe_locator_key_is_rejected_before_provenance_capture():
    observation = _github_observation(token="plaintext-credential")
    result = bind_provider_observations([observation], [_github_binding()])

    assert result["status"] == "UNKNOWN"
    assert result["provenance"] == []
    assert result["binding_issues"][0]["reason"] == "UNSAFE_LOCATOR"


def test_inputs_are_not_mutated_and_hash_is_normalized():
    observation = _github_observation()
    observation["content_sha256"] = "A" * 64
    binding = _github_binding()
    original_observation = deepcopy(observation)
    original_binding = deepcopy(binding)

    result = bind_provider_observations([observation], [binding])

    assert observation == original_observation
    assert binding == original_binding
    assert result["provenance"][0]["content_sha256"] == "a" * 64
