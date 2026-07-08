# ADR 0001: Use CyberCore as the control-plane repository

Date: 2026-07-08  
Status: Accepted

## Context

The project needs to manage InterServer shared hosting, VPS, DirectAdmin, mail, DNS, WordPress, Nextcloud, documentation, monitoring, security and future AI-assisted operations.

## Decision

Use `cyberDJs/CyberCore` as the main control-plane repository for project documentation, roadmap, architecture, automation and operational procedures.

## Consequences

- CyberCore is not just a website repository.
- Private environment-specific data must be separated from reusable framework logic.
- The repository should remain private until sanitization rules are implemented.
