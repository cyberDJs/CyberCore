# ADR-0011: Cyber Voice Intelligence Bridge

Date: 2026-09-02
Status: Accepted for WB-0039 implementation

## Context

WB-0036 established vendor-neutral voice intent and governance contracts. WB-0037 added realtime
audio and barge-in. WB-0038 added local microphone, STT, TTS, and speaker adapters. The remaining
local loop still used `RuleIntentCompiler` and `NoopActionPlanner`, so normal conversation and
multilingual interpretation were intentionally limited.

A model can improve interpretation and response quality, but placing a generative model on the
authority path would violate CyberCore's exact-plan approval and evidence model.

## Decision

Add a model-backed intelligence layer before the existing governed router with these constraints:

1. Authority-sensitive `CANCEL`, `APPROVE`, and `EXECUTE` intents are classified deterministically
   before any model call.
2. Those intent kinds are absent from the model JSON Schema and cannot be returned by the model.
3. Model output is strict, structured, confidence-bounded, and rejected on schema mismatch.
4. Failure falls back safely; authority-sensitive fallback classifications are downgraded to
   `UNKNOWN`.
5. Current or changing external-state questions are marked `needs_live_data` and are not answered
   from model memory.
6. Stable general-knowledge questions may be answered by a bounded response composer.
7. Operational intents continue through the existing VoiceRouter, HOWEDO, OATHDO, CCL approval,
   and governed execution boundaries.
8. The first provider is local Ollama over explicit loopback HTTP using only the Python standard
   library. No model is downloaded or started automatically.

## Consequences

Cyber Voice can gain multilingual interpretation and conversational responses without expanding
tool permissions. A compromised or hallucinating model still cannot mint approval or execution
authority through its output contract.

The design deliberately stops short of answering current project or infrastructure questions.
Those require a separately permissioned read-only tool router.

## Alternatives rejected

### Put the LLM directly inside VoiceRouter authority decisions

Rejected because model output would become coupled to approval and execution semantics.

### Let the model emit every IntentKind

Rejected because prompt injection or malformed output could create authority-sensitive intent
classes. Deterministic classification is simpler to audit.

### Add a cloud model SDK in the core package

Rejected for this work block because it adds credentials, network trust, dependency weight, and
provider lock-in before the local reference path is proven.

### Let general answers use model memory for current state

Rejected because it creates an avoidable hallucination path. Current state must come from a
permitted evidence source.

## Rollback

The change is source-only. Removing the intelligence package and the optional local-runtime hook
restores WB-0038 behavior. No database, secret, model, external service, or production migration is
required for rollback.
