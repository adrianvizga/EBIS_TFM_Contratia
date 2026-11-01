const userTimezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;

// El backend envía fechas sin sufijo de zona horaria — se tratan como UTC.
function toUtcDate(isoString: string): Date {
  const hasTimezone = isoString.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(isoString);
  return new Date(hasTimezone ? isoString : isoString + 'Z');
}

export function formatDateTime(isoString: string, language: string): string {
  if (!isoString) return '';
  const date = toUtcDate(isoString);
  if (isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat(language, {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
    timeZone: userTimezone(),
  }).format(date);
}

export function formatDate(isoString: string, language: string): string {
  if (!isoString) return '';
  const date = toUtcDate(isoString);
  if (isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat(language, {
    year: 'numeric', month: '2-digit', day: '2-digit',
    timeZone: userTimezone(),
  }).format(date);
}

export function formatDateLong(isoString: string, language: string): string {
  if (!isoString) return '';
  const date = toUtcDate(isoString);
  if (isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat(language, {
    day: '2-digit', month: 'long', year: 'numeric',
    timeZone: userTimezone(),
  }).format(date);
}

export function formatTime(isoString: string, language: string): string {
  if (!isoString) return '';
  const date = toUtcDate(isoString);
  if (isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat(language, {
    hour: '2-digit', minute: '2-digit',
    timeZone: userTimezone(),
  }).format(date);
}

export function formatRelative(
  isoString: string,
  language: string,
  t: (key: string) => string,
): string {
  if (!isoString) return '';
  const date = toUtcDate(isoString);
  if (isNaN(date.getTime())) return isoString;
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return t('agent.now');
  if (mins < 60) return t('agent.minutesAgo').replace('{n}', String(mins));
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t('agent.hoursAgo').replace('{n}', String(hours));
  return new Intl.DateTimeFormat(language, {
    day: '2-digit', month: 'short',
    timeZone: userTimezone(),
  }).format(date);
}
