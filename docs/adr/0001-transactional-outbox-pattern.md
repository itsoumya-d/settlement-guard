# ADR 0001: Transactional Outbox Pattern for Asynchronous Clearing

## Status
Accepted

## Context
Dual-writing to an event bus and relational database during high-frequency settlement creates distributed state inconsistency when one system fails.

## Decision
We adopted the Transactional Outbox pattern where settlement records and outbox event records are committed inside a single ACID database transaction.

## Consequences
- Positive: Guaranteed at-least-once delivery with zero phantom settlement records.
- Negative: Requires an outbox poller or CDC worker.
