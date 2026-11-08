# The pain point

## Public evidence

| Signal | Evidence | Link |
| --- | --- | --- |
| 23 incidents in 90 days, 98.26% uptime | Pingoru Paymark outage history | <https://pingoru.io/providers/paymark/outage-history> |
| MPGS settlement delay | "Paymark is aware of a delay to settlement of some MPGS ecommerce transactions from 1 November. As a result of this delay, some merchants may not have received their settlement overnight for this date as expected." | <https://pingoru.io/providers/paymark> |
| Incomplete transaction reporting | "Transaction reporting data for 27/10/2026 may be incomplete due to this issue." | <https://pingoru.io/providers/paymark/outage-history> |
| Spark connectivity outage | 10 hours 21 minutes affecting terminal connectivity to Paymark | <https://pingoru.io/providers/paymark/incidents/12456415> |
| South Island EFTPOS outage | EFTPOS connections incorrectly routed, affecting Paymark transactions | <https://www.reseller.co.nz/article/4243656/spark-investigates-cause-of-south-island-eftpos-outage.html> |
| Official status surface | Paymark status page | <https://status.paymark.co.nz> |
| Public developer API | Online EFTPOS, CLICK, Linked Gateway | <https://developer.paymark.co.nz/> |

The ad that triggered this build (Senior Software Engineer, Auckland) asked for AWS, Java, Python, MySQL, Unix, Git, CI/CD, HTTP/TLS and a 5+ year engineer to build scalable, reliable payment systems. The ad closed after nine days, but the operational problem it describes is live and public.

## The failure mode

When an upstream network or bank connection fails, the recovery path creates three classes of work:

1. **Settlement arrives before authorization** — the settlement cannot be posted, but dropping it loses merchant money and breaks reconciliation.
2. **A settlement file is replayed** — naive processing posts the same settlement twice and overstates the merchant payable.
3. **A settlement file is delayed or incomplete** — finance sees a break but cannot tell whether the transaction is missing, late, duplicated or mismatched.

The public incident wording shows the commercial consequence: merchants may not receive overnight settlement, and reporting data may be incomplete. The fix has to make those states explicit, recoverable and auditable.

## The shipped fix

| Control | Implementation |
| --- | --- |
| Do not drop out-of-order settlements | `PaymentEventService` parks `SETTLEMENT`/`CLEARING` with `AUTHORIZATION_NOT_SEEN` and applies it when the authorization arrives |
| Do not double-post a replay | Unique `(terminal_id, stan, rrn, event_type)` plus payload hash; replay returns `DUPLICATE`, different payload returns `409` |
| Keep the books balanced | Every event posts a debit and a credit; dashboard exposes totals and a balanced flag |
| Make breaks explicit | `ReconciliationService` classifies `MISSING_AUTHORIZATION`, `DUPLICATE_SETTLEMENT`, `AMOUNT_MISMATCH`, `DELAYED_SETTLEMENT` |
| Make failures visible | Micrometer counters, Prometheus endpoint, Terraform CloudWatch alarms for parked settlements and breaks |
| Preserve an audit trail | SHA-256 hash chain over audit records with tamper detection |
| Give operations a view | Paymark-token dashboard for events, parked settlements, breaks and ledger status |

## Commercial value

- Fewer merchant support calls during an upstream incident: the parked queue is visible instead of silent.
- Faster finance close: breaks are classified, not discovered manually.
- Lower double-settlement risk: idempotency is enforced at the event boundary.
- Better incident review: the audit chain records what happened and in what order.

## What is deliberately not claimed

This is a clean-room reference implementation. It does not connect to the live Paymark switch, process real card data, claim PCI-DSS certification, or reuse any proprietary code. It demonstrates the engineering shape of the fix against public evidence.
