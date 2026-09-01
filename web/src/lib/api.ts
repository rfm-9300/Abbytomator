const KEY = "abbitAuth";

export function setAuth(user: string, password: string): void {
  sessionStorage.setItem(KEY, btoa(`${user}:${password}`));
}

export function clearAuth(): void {
  sessionStorage.removeItem(KEY);
}

export function hasAuth(): boolean {
  return Boolean(sessionStorage.getItem(KEY));
}

function authHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  const token = sessionStorage.getItem(KEY);
  if (token) headers.set("Authorization", `Basic ${token}`);
  return headers;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = authHeaders(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  if (response.status === 401) {
    clearAuth();
    if (!location.pathname.startsWith("/login")) location.replace("/login/");
    throw new Error("unauthorized");
  }
  if (!response.ok) {
    const text = await response.text();
    let message = text || response.statusText;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* not JSON */
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function download(path: string, filename: string): Promise<void> {
  const response = await fetch(path, { headers: authHeaders() });
  if (response.status === 401) {
    clearAuth();
    location.replace("/login/");
    throw new Error("unauthorized");
  }
  if (!response.ok) throw new Error(await response.text());
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export type Campaign = {
  id: number;
  name: string;
  platform: string;
  status: string;
  event_label: string;
  last_imported_at: string | null;
  locations: LocationRow[];
  amount_spent?: number;
  clicks?: number;
  impressions?: number | null;
  ctr?: number | null;
  cpc?: number | null;
  tix_sold?: number;
  cpp?: number | null;
};

export type LocationRow = {
  id: number;
  name: string;
  status?: string;
  amount_spent?: number | null;
  clicks?: number;
  tix_sold?: number;
  cpc?: number | null;
  cpp?: number | null;
  note?: string;
  tix_history?: (number | null)[];
};

export type Week = {
  id: number;
  period_end: string;
  updated_until: string | null;
  label?: string;
  notes: string;
};

export type CampaignNotes = Campaign & {
  note?: string;
  performance_summary?: string;
  next_steps?: string;
  show_city_clicks?: boolean;
  locations: LocationRow[];
};

export type Overview = {
  week: Week | null;
  account_manager?: string;
  history?: { id: number; label: string; period_end: string }[];
  history_totals?: { id: number; label: string; totals: Totals }[] | null;
  previous?: { label: string; totals: Totals } | null;
  has_structured_notes?: boolean;
  groups: {
    event_label: string;
    campaigns: CampaignNotes[];
    totals: Totals;
  }[];
  totals: Totals;
};

export type Totals = {
  amount_spent: number;
  clicks: number;
  tix_sold: number;
  cpc: number | null;
  cpp: number | null;
};
