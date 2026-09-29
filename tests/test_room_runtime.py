from cybercore.mcp.room_broker import ALLOWED_CHATGPT_IDENTITIES, PARTICIPANT_ROLES


def test_room_runtime_identity_allowlist_is_exact():
    assert ALLOWED_CHATGPT_IDENTITIES == frozenset(
        {"chatgpt:johnny-work", "chatgpt:johnny-mod", "chatgpt:eimy"}
    )
    assert "chatgpt:johnny" not in ALLOWED_CHATGPT_IDENTITIES
    assert "chatgpt:anyone" not in ALLOWED_CHATGPT_IDENTITIES


def test_room_runtime_participant_roles_are_explicit_and_non_privileged_by_default():
    assert PARTICIPANT_ROLES == {
        "chatgpt:johnny-work": "participant",
        "chatgpt:johnny-mod": "moderator",
        "chatgpt:eimy": "participant",
    }
