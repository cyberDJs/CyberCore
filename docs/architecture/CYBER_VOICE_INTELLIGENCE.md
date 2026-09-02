# Cyber Voice Intelligence Bridge

Status: WB-0039 implementation
Date: 2026-09-02

## Purpose

WB-0039 adds a model-backed interpretation and general-knowledge response layer to Cyber Voice
without moving execution authority into the model. It sits between the existing `Utterance`
contract and the WB-0036 `VoiceRouter` boundary.

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
                          | live data    | stable question
                          v              v
                   needs read-only    model response
                        tool             composer
                          \              /
                           \            /
                            spoken response -> TTS
```

## Authority boundary

`CANCEL`, `APPROVE`, and `EXECUTE` are deliberately absent from the model output schema. A model
cannot create those intent kinds even if it is prompted or compromised to do so. Command-like
forms of those intents are classified by a deterministic pre-model guard.

If model classification fails, the fallback rule compiler is sanitized: any authority-sensitive
fallback result is downgraded to `UNKNOWN`. This prevents a phrase that merely mentions a word
such as "approve" from becoming an approval intent during model failure.

A voice approval remains only `VoiceApprovalIntent`. Existing exact-plan approval verification and
the governed execution bridge remain downstream and authoritative.

## Structured intent contract

The model may return only:

- `question`
- `search`
- `inspect`
- `plan`
- `monitor`
- `unknown`

The response must contain exactly `kind`, `operation`, `target`, `language`, `confidence`, and
`needs_live_data`. Extra or missing fields fail closed. The default confidence threshold is 0.75.

## Live-data rule

The intelligence bridge has no read-only tools in WB-0039. Questions about current repository,
CI, service, machine, infrastructure, or other changing state must set `needs_live_data=true`.
The controller then refuses to synthesize a factual answer and states that an allowed read-only
tool is required. Read-only tool routing is deferred to the next work block.

Stable general-knowledge questions may be answered by the response composer. The composer is told
that it has no current external state and must never claim that an action was executed, approved,
scheduled, or verified.

## Local Ollama reference provider

The reference provider accepts only an explicit loopback HTTP endpoint (`localhost`, `127.0.0.1`,
or `::1`). Credentials, non-loopback hosts, URL paths, query strings, and fragments are rejected.
The client calls `/api/chat` with streaming disabled, thinking disabled, temperature zero, and a
JSON Schema in `format` for classification.

Example configuration:

```json
{
  "enabled": true,
  "provider": "ollama",
  "model": "qwen3:4b",
  "base_url": "http://127.0.0.1:11434",
  "timeout_s": 12,
  "min_confidence": 0.75,
  "max_answer_chars": 1200
}
```

The default path is `~/.config/cybercore/voice-intelligence.json`. A local speech session remains
unchanged unless an enabled intelligence configuration is explicitly supplied to `voice local`.
No model is downloaded automatically.

## Local CLI integration

```bash
cybercore voice local \
  --config ~/.config/cybercore/voice-local.json \
  --intelligence-config ~/.config/cybercore/voice-intelligence.json
```

Without `--intelligence-config`, WB-0038 behavior is preserved exactly.

## Evaluation

The repository includes a 75-case starter fixture:

- 20 normal Czech utterances
- 10 English utterances
- 10 Czech/English mixed and slang utterances
- 10 STT-like noisy utterances
- 15 authority-sensitive utterances
- 10 live-state versus general-knowledge questions

CI validates the fixture shape and requires every authority case to be captured before the model.
Unit tests also cover strict schema parsing, invalid JSON, low confidence, model outages,
loopback-only transport, live-data refusal, and unchanged downstream governance routing.

The fixture is not a claim of model accuracy by itself. Model-specific accuracy must be measured
against an actually installed model before promoting that model as a supported default.

## Non-goals

WB-0039 does not add:

- tool execution or tool calling;
- shell or SSH access;
- GitHub, Slack, Drive, browser, or infrastructure actions;
- automatic Ollama startup or model download;
- CASEBOOK/CASER persistence;
- speaker authentication;
- cloud AI credentials;
- new approval or execution authority.

## Next boundary

The intended successor is a bounded read-only tool router. It can satisfy `needs_live_data`
requests while keeping model interpretation separate from tool permissions and mutation authority.
