# ADR 0002: Flyway Versioned Migrations for Database Schema Lifecycle

## Status
Accepted

## Context
Payment schema changes must be applied deterministically across CI, staging, and production without downtime or schema drift.

## Decision
We enforce Flyway versioned SQL migrations located in `src/main/resources/db/migration` managed as code.

## Consequences
- Positive: Predictable, testable schema rollouts verified in CI using Testcontainers.
- Negative: Backward-incompatible column drops require phased two-release deprecation.
