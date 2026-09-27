from pathlib import Path


def test_pipe_is_async_identity_bound_and_avoids_embedded_secrets():
    source = Path("integrations/openwebui/cyberdjs_room_pipe.py").read_text()
    assert "async def pipe" in source
    assert "__chat_id__" in source
    assert "__session_id__" in source
    assert "__user__" in source
    assert "API_KEY" not in source
    assert "password" not in source.lower()
    assert "/v1/rooms/message" in source
