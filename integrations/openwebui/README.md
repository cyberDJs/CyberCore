# Open WebUI — CyberDJs Room Pipe

`cyberdjs_room_pipe.py` is reviewed source for an Open WebUI Pipe Function. It presents one
`CyberDJs Room` model and forwards the authenticated Open WebUI user/chat/session identity to a
narrow CyberCore room endpoint.

Open WebUI Functions execute server-side Python. Import/enable only after code review and only from
this controlled source. Runtime installation and endpoint deployment are separate approval-gated
operations.

The Pipe does not make Open WebUI the source of truth. It forwards one user turn and renders ordered
agent-labelled replies returned by CyberCore.
