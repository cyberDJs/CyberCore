# Cyber Voice Intelligence Bridge

Status: WB-0039 forward-port
Date: 2026-09-19

## Purpose

WB-0039 adds a model-backed interpretation and general-knowledge response layer to Cyber Voice
without moving execution authority into the model. It sits between the existing `Utterance`
contract and the governed `VoiceRouter` boundary.

The reference model transport is a local-only Ollama adapter implemented with the Python standard
library. No cloud credential, model download, shell execution, GitHub mutation, or infrastructure
executor is added by this work block.

## Runtime flow

```text
speech -> STT -> Utterance
                 |
                 v
        deterministic safety guard
          |                  |
          | authority intent | ordinary intent
          v                  v
 existing VoiceRouter   structured model compiler
 HOWEDO/OATHDO/CCL        |              |
                          | source needed | lexical definition
                          v               v
                   needs read-only     model response
                        tool              composer
                          \              /
                           \            /
                            spoken response -> TTS
```

## Authority boundary

`CANCEL`, `APPROVE`, and `EXECUTE` are deliberately absent from the model output schema. A model
cannot create those intent kinds even if prompted or compromised. Command-like forms are classified
by a deterministic pre-model guard. Cancellation requires a bounded marker in recognized command
syntax (for example a direct imperative or an explicit second-person request). Bare marker mentions,
questions, descriptions, quoted/definition uses, and locally negated commands remain non-cancelling.

If model classification fails, the fallback rule compiler is sanitized: any authority-sensitive
fallback result is downgraded to `UNKNOWN`.

A voice approval remains only intent. Existing exact-plan approval verification and governed
execution boundaries remain downstream and authoritative.

## Structured intent contract

The model may return only `question`, `search`, `inspect`, `plan`, `monitor`, or `unknown`.
The response must contain exactly `kind`, `operation`, `target`, `language`, `confidence`, and
`needs_live_data`. Extra or missing fields fail closed.

## Live-data rule

The intelligence bridge has no read-only tools in WB-0039. Model questions fail closed unless the
utterance is an explicit one-term lexical-definition request such as `what does TERM mean` or
`define TERM` (including Czech equivalents). Broad factual forms such as `what is ...` and
mechanistic forms such as `how does ... work` are not trusted as evidence of stability. Search,
inspect, monitor and every non-allowlisted question therefore require a trusted source regardless of
a model-supplied `needs_live_data=false`; a model-supplied `needs_live_data=true` remains additive.

## Local Ollama reference provider

Only explicit loopback HTTP endpoints are accepted. Credentials, non-loopback hosts, URL paths,
query strings, and fragments are rejected. The HTTP client disables environment proxies and rejects
redirects, preserving the local-only transport boundary even on hosts with proxy variables set. No
model is downloaded automatically.

While model inference is synchronous, local microphone input is pumped through
`RealtimeVoiceRuntime.receive_input`. Speech detected in `PROCESSING` therefore triggers the
existing interrupt/barge-in transition, and the completed stale model answer is not spoken while the
runtime is interrupted.

## Local CLI integration

```bash
cybercore voice local \
  --config ~/.config/cybercore/voice-local.json \
  --intelligence-config ~/.config/cybercore/voice-intelligence.json
```

Without `--intelligence-config`, current local voice behavior is preserved.

## Non-goals

WB-0039 does not add tool execution, shell or SSH access, GitHub/Slack/Drive/browser actions,
automatic model startup/download, cloud credentials, or new approval/execution authority.
