const state = {
    summaryUrl: '/api/v1/dashboard/summary',
    eventsUrl: '/api/v1/payments?limit=10'
};

function text(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function money(cents) {
    return new Intl.NumberFormat('en-NZ', {
        style: 'currency',
        currency: 'NZD',
        maximumFractionDigits: 2
    }).format((cents || 0) / 100);
}

function statusBadge(status) {
    const span = document.createElement('span');
    span.className = 'badge badge--' + String(status || '').toLowerCase();
    span.textContent = status || 'UNKNOWN';
    return span;
}

async function loadSummary() {
    const response = await fetch(state.summaryUrl, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
        throw new Error('Summary request failed');
    }
    const data = await response.json();

    text('events-total', data.events.total);
    text('events-meta', data.events.applied + ' applied · ' + data.events.duplicate + ' duplicate');
    text('events-parked', data.events.parked);
    text('breaks-total', data.reconciliation.breaks);
    text('ledger-status', data.ledger.balanced ? 'Balanced' : 'Out of balance');
    text('ledger-meta', money(data.ledger.debits) + ' debits · ' + money(data.ledger.credits) + ' credits');

    const latest = data.reconciliation.latestRunId
        ? 'Run ' + data.reconciliation.latestRunId + ' · ' + data.reconciliation.latestStatus
        : 'No reconciliation run yet.';
    text('latest-run', latest);
}

async function loadEvents() {
    const response = await fetch(state.eventsUrl, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
        throw new Error('Events request failed');
    }
    const events = await response.json();
    const body = document.getElementById('events-body');
    body.replaceChildren();

    if (!events.length) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 5;
        cell.textContent = 'No payment events yet.';
        row.appendChild(cell);
        body.appendChild(row);
        return;
    }

    for (const event of events) {
        const row = document.createElement('tr');
        const rrn = document.createElement('td');
        rrn.textContent = event.rrn;
        const type = document.createElement('td');
        type.textContent = event.eventType;
        const amount = document.createElement('td');
        amount.textContent = money(event.amountCents);
        const status = document.createElement('td');
        status.appendChild(statusBadge(event.status));
        const received = document.createElement('td');
        received.textContent = new Date(event.receivedAt).toLocaleString('en-NZ');
        row.append(rrn, type, amount, status, received);
        body.appendChild(row);
    }
}

async function refresh() {
    try {
        await Promise.all([loadSummary(), loadEvents()]);
    } catch (error) {
        text('events-meta', 'Unable to load data');
    }
}

document.getElementById('refresh').addEventListener('click', refresh);
refresh();
