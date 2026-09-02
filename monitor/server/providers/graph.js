import { makeEntity } from '../model.js';
import { auth } from '../auth.js';

const GRAPH = 'https://graph.microsoft.com/v1.0';

async function get(token, path) {
  const res = await fetch(`${GRAPH}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = new Error(`${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// Thresholds for "this needs a human". Tuned to be quiet: a monitor that cries
// wolf about a 12-message inbox trains you to ignore the beacons.
const INBOX_WARN = 40;
const INBOX_FAIL = 150;
const SUBSCRIPTION_WARN_MINUTES = 120;

export class GraphProvider {
  id = 'graph';
  label = 'Microsoft 365';

  async fetch() {
    const token = await auth.token('graph', { interactive: false });
    if (!token) return [];

    const entities = [];
    const settle = async (label, fn) => {
      try {
        await fn();
      } catch (err) {
        // One unavailable Graph endpoint must not blank the whole district.
        console.warn(`[graph] ${label}: ${err.message}`);
      }
    };

    await settle('mail folders', async () => {
      const data = await get(token, '/me/mailFolders?$top=20');
      for (const folder of data.value ?? []) {
        if (!['Inbox', 'Drafts', 'Archive'].includes(folder.displayName)) continue;
        const unread = folder.unreadItemCount ?? 0;
        let status = 'healthy';
        if (unread >= INBOX_FAIL) status = 'failed';
        else if (unread >= INBOX_WARN) status = 'warning';

        entities.push(
          makeEntity({
            id: `graph:folder:${folder.id}`,
            source: 'graph',
            district: 'Mailbox',
            kind: 'mailbox',
            name: folder.displayName,
            status,
            detail: `${unread} unread of ${folder.totalItemCount ?? 0}`,
            weight: 0.8 + Math.min(2, unread / 60),
            url: 'https://outlook.office.com/mail/',
            metrics: { unread, total: folder.totalItemCount ?? 0 },
            actions: [],
          }),
        );
      }
    });

    await settle('message rules', async () => {
      const data = await get(token, '/me/mailFolders/inbox/messageRules');
      const rules = data.value ?? [];
      const disabled = rules.filter((r) => r.isEnabled === false);
      entities.push(
        makeEntity({
          id: 'graph:rules',
          source: 'graph',
          district: 'Mailbox',
          kind: 'watchdog',
          name: 'Inbox rules',
          status: disabled.length ? 'warning' : 'healthy',
          detail: disabled.length
            ? `${disabled.length} rule(s) disabled: ${disabled.map((r) => r.displayName).join(', ')}`
            : `${rules.length} rules, all enabled`,
          weight: 1,
          url: 'https://outlook.office.com/mail/options/mail/rules',
          metrics: { total: rules.length, disabled: disabled.length },
          actions: [],
        }),
      );
    });

    await settle('subscriptions', async () => {
      const data = await get(token, '/subscriptions');
      for (const sub of data.value ?? []) {
        const minutesLeft = (new Date(sub.expirationDateTime) - Date.now()) / 60000;
        let status = 'healthy';
        if (minutesLeft <= 0) status = 'failed';
        else if (minutesLeft < SUBSCRIPTION_WARN_MINUTES) status = 'blocked';

        entities.push(
          makeEntity({
            id: `graph:sub:${sub.id}`,
            source: 'graph',
            district: 'Graph Subscriptions',
            kind: 'subscription',
            name: sub.resource ?? sub.id,
            status,
            detail:
              minutesLeft <= 0
                ? 'Expired — webhook is no longer delivering'
                : `Renews in ${Math.round(minutesLeft)}m`,
            weight: 1.4,
            url: null,
            metrics: { expirationDateTime: sub.expirationDateTime, minutesLeft },
            actions: [],
          }),
        );
      }
    });

    await settle('calendar', async () => {
      const start = new Date();
      const end = new Date(Date.now() + 86400000);
      const data = await get(
        token,
        `/me/calendarView?startDateTime=${start.toISOString()}&endDateTime=${end.toISOString()}&$top=50`,
      );
      const events = (data.value ?? []).filter((e) => !e.isCancelled);
      const conflicts = countOverlaps(events);
      entities.push(
        makeEntity({
          id: 'graph:calendar',
          source: 'graph',
          district: 'Mailbox',
          kind: 'calendar',
          name: 'Next 24 hours',
          status: conflicts ? 'warning' : 'healthy',
          detail: conflicts
            ? `${conflicts} overlapping meeting(s)`
            : `${events.length} meetings, no conflicts`,
          weight: 0.9 + Math.min(1.5, events.length / 10),
          url: 'https://outlook.office.com/calendar/',
          metrics: { events: events.length, conflicts },
          actions: [],
        }),
      );
    });

    return entities;
  }

  async execute() {
    // Everything here is read-only by design: the Graph surfaces this tool reads
    // are signals, and mutating mail or calendar from a game map is a bad idea.
    return { ok: false, message: 'Microsoft 365 signals are read-only in this build' };
  }
}

function countOverlaps(events) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.start?.dateTime ?? 0) - new Date(b.start?.dateTime ?? 0),
  );
  let conflicts = 0;
  for (let i = 1; i < sorted.length; i++) {
    const prevEnd = new Date(sorted[i - 1].end?.dateTime ?? 0);
    const thisStart = new Date(sorted[i].start?.dateTime ?? 0);
    if (thisStart < prevEnd) conflicts++;
  }
  return conflicts;
}
