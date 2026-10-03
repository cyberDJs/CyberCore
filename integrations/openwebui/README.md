# Open WebUI — CyberDJs Room Pipe

`cyberdjs_room_pipe.py` is reviewed source for an Open WebUI Pipe Function. It presents one
`CyberDJs Room` model and forwards the authenticated Open WebUI user/chat/session identity to the
loopback CyberCore room endpoint.

The JSON body intentionally contains no `actor_id`. The Pipe takes `__user__.id` from Open
WebUI's trusted function context and sends it as `X-CyberDJS-User-ID`. CyberCore derives the
canonical actor ID as `openwebui:<user-id>`.

Open WebUI Functions execute server-side Python. Import/enable only after code review and only from
this controlled source. Runtime installation and endpoint deployment are separate approval-gated
operations.

The current HTTP adapter is loopback-only. Loopback confinement is not cryptographic client
authentication; LAN/public exposure requires a separately reviewed authenticated transport.

The Pipe does not make Open WebUI the source of truth. It forwards one user turn and renders ordered
agent-labelled replies returned by CyberCore.
