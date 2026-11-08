# AGENTS.md

## Project

Settlement Guard is a clean-room payment settlement and reconciliation engine built to demonstrate the Paymark/Worldline NZ Senior Software Engineer brief: Java 17, Spring Boot, AWS, MySQL, Python, Kafka, CI/CD and payments reliability.

## Commands

```bash
./gradlew test
./gradlew bootRun --args='--spring.profiles.active=local'
python -m pytest tools -q
docker compose up --build
```

## Conventions

- Java 17, constructor injection, records for DTOs.
- Every external effect gets a test; every financial posting must balance.
- Never commit credentials, real merchant data or production endpoint secrets.
- Keep the public incident evidence in `docs/pain-point.md` linked and current.
- Preserve the Paymark design tokens in `docs/design-tokens.md` and `styles.css`.
- Update `docs/evidence-matrix.md` when adding a role-relevant capability.

## Boundaries

- Clean-room only: no proprietary Paymark code, assets, customer data or internal systems.
- No claim of PCI-DSS certification, HSM operations or live switch access.
- No payment card data should ever be added to this repository.
