CREATE TABLE payment_events (
    id VARCHAR(36) NOT NULL,
    terminal_id VARCHAR(32) NOT NULL,
    stan VARCHAR(12) NOT NULL,
    rrn VARCHAR(32) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    amount_cents BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    event_time TIMESTAMP(6) NOT NULL,
    sequence_no BIGINT NOT NULL,
    payload_hash VARCHAR(128) NOT NULL,
    status VARCHAR(24) NOT NULL,
    parked_reason VARCHAR(120) NULL,
    received_at TIMESTAMP(6) NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT uk_payment_event UNIQUE (terminal_id, stan, rrn, event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_payment_events_rrn ON payment_events (rrn);
CREATE INDEX idx_payment_events_status ON payment_events (status);

CREATE TABLE ledger_entries (
    id VARCHAR(36) NOT NULL,
    event_id VARCHAR(36) NOT NULL,
    account VARCHAR(64) NOT NULL,
    debit_cents BIGINT NOT NULL,
    credit_cents BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    posted_at TIMESTAMP(6) NOT NULL,
    description VARCHAR(160) NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_ledger_entries_event ON ledger_entries (event_id);

CREATE TABLE reconciliation_runs (
    id VARCHAR(36) NOT NULL,
    filename VARCHAR(160) NOT NULL,
    status VARCHAR(24) NOT NULL,
    total_rows INT NOT NULL,
    matched INT NOT NULL DEFAULT 0,
    missing_authorization INT NOT NULL DEFAULT 0,
    duplicate_settlements INT NOT NULL DEFAULT 0,
    amount_mismatches INT NOT NULL DEFAULT 0,
    delayed_settlements INT NOT NULL DEFAULT 0,
    started_at TIMESTAMP(6) NOT NULL,
    completed_at TIMESTAMP(6) NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE reconciliation_breaks (
    id VARCHAR(36) NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    rrn VARCHAR(32) NOT NULL,
    break_type VARCHAR(32) NOT NULL,
    expected_cents BIGINT NULL,
    actual_cents BIGINT NULL,
    detail VARCHAR(255) NULL,
    created_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_reconciliation_breaks_run ON reconciliation_breaks (run_id);
CREATE INDEX idx_reconciliation_breaks_type ON reconciliation_breaks (break_type);

CREATE TABLE audit_records (
    id VARCHAR(36) NOT NULL,
    sequence BIGINT NOT NULL,
    event_id VARCHAR(36) NOT NULL,
    previous_hash VARCHAR(64) NULL,
    hash VARCHAR(64) NOT NULL,
    payload VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE UNIQUE INDEX uk_audit_records_sequence ON audit_records (sequence);
CREATE INDEX idx_audit_records_event ON audit_records (event_id);
CREATE INDEX idx_audit_records_created ON audit_records (created_at);
