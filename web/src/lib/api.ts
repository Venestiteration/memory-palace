import type {
  HealthResponse,
  MetricsResponse,
  CaptureTextRequest,
  CaptureTextResponse,
  InboxResponse,
  AskRequest,
  AskResponse,
  BriefResponse,
} from './types';

const getBaseUrl = () =>
  localStorage.getItem('mp_api_url') || 'http://127.0.0.1:8000';

const getToken = () => localStorage.getItem('mp_api_token') || '';

const getHeaders = () => {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

export const getHealth = () =>
  fetch(`${getBaseUrl()}/health/detailed`, {
    headers: getHeaders(),
  }).then((r) => r.json() as Promise<HealthResponse>);

export const getMetrics = () =>
  fetch(`${getBaseUrl()}/metrics`, {
    headers: getHeaders(),
  }).then((r) => r.json() as Promise<MetricsResponse>);

export const captureText = (data: CaptureTextRequest) =>
  fetch(`${getBaseUrl()}/capture/text`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  }).then((r) => r.json() as Promise<CaptureTextResponse>);

export const getInbox = (limit?: number) => {
  const url = new URL(`${getBaseUrl()}/inbox`);
  if (limit) url.searchParams.set('limit', String(limit));
  return fetch(url.toString(), {
    headers: getHeaders(),
  }).then((r) => r.json() as Promise<InboxResponse>);
};

export const ask = (data: AskRequest) =>
  fetch(`${getBaseUrl()}/ask`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  }).then((r) => r.json() as Promise<AskResponse>);

export const getDailyBrief = (date?: string) => {
  const url = new URL(`${getBaseUrl()}/brief/daily`);
  if (date) url.searchParams.set('date', date);
  return fetch(url.toString(), {
    headers: getHeaders(),
  }).then((r) => r.json() as Promise<BriefResponse>);
};

export const getWeeklyBrief = (week?: string) => {
  const url = new URL(`${getBaseUrl()}/brief/weekly`);
  if (week) url.searchParams.set('week', week);
  return fetch(url.toString(), {
    headers: getHeaders(),
  }).then((r) => r.json() as Promise<BriefResponse>);
};

export const generateDailyBrief = (date?: string) =>
  fetch(`${getBaseUrl()}/brief/daily/generate`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ date }),
  }).then((r) => r.json() as Promise<BriefResponse>);

export const generateWeeklyBrief = (week?: string) =>
  fetch(`${getBaseUrl()}/brief/weekly/generate`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ week }),
  }).then((r) => r.json() as Promise<BriefResponse>);