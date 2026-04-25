export function pad(n: number, w = 2): string {
  return String(n).padStart(w, "0");
}

export function formatUTC(d: Date): string {
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`;
}

export function formatDate(d: Date): string {
  const m = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  return `${pad(d.getUTCDate())} ${m[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}
