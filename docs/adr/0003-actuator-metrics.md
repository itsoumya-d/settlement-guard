# ADR 0003: Actuator and Micrometer Prometheus Metrics for Operational Visibility

## Status
Accepted

## Context
Production settlement failures must be surfaced immediately without manual log inspection.

## Decision
We expose standardized Prometheus metrics via `/actuator/prometheus` and readiness checks via `/actuator/health`.

## Consequences
- Positive: Instant ingestion into Grafana dashboards and PagerDuty alert triggers.
- Negative: Endpoint security filter required to restrict actuator exposure to internal networks.
