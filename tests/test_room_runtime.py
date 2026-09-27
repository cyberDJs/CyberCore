from cybercore.mcp.room_runtime import ALLOWED_CHATGPT_IDENTITIES


def test_room_runtime_identity_allowlist_is_exact():
    assert ALLOWED_CHATGPT_IDENTITIES == frozenset({"chatgpt:johnny", "chatgpt:eimy"})
    assert "chatgpt:anyone" not in ALLOWED_CHATGPT_IDENTITIES
