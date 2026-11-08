# Security policy

## Reporting

Email **soumyadebnath1619@gmail.com** with a description, reproduction steps and impact. Do not open a public issue for a suspected vulnerability.

## Controls in this repository

- Idempotency key and payload hash on every payment event.
- Double-entry ledger and reconciliation classification.
- SHA-256 hash-chained audit records with sequence ordering.
- Validation on every HTTP request.
- No card data, credentials or merchant data in the repository.
- Container runs as a non-root user.
- Kubernetes security context drops Linux capabilities.
- Terraform provisions SQS encryption, a DLQ and CloudWatch alarms.
- CI runs tests, Python controls, Terraform validation and a Docker build.

## Out of scope

- Live Paymark/Worldline credentials or production switch access.
- PCI-DSS certification, HSM operations, key ceremony and card-data handling.
- WAF, mTLS, KMS rotation and WORM audit storage. Production should add these.
