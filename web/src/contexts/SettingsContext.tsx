import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface Settings {
  apiUrl: string;
  token: string;
}

interface SettingsContextValue {
  settings: Settings;
  updateSettings: (s: Settings) => void;
  isConfigured: boolean;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

const API_URL_KEY = 'mp_api_url';
const API_TOKEN_KEY = 'mp_api_token';
const DEFAULT_API_URL = 'http://127.0.0.1:8000';

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => ({
    apiUrl: localStorage.getItem(API_URL_KEY) || DEFAULT_API_URL,
    token: localStorage.getItem(API_TOKEN_KEY) || '',
  }));

  const updateSettings = useCallback((s: Settings) => {
    localStorage.setItem(API_URL_KEY, s.apiUrl);
    localStorage.setItem(API_TOKEN_KEY, s.token);
    setSettings(s);
  }, []);

  const isConfigured = Boolean(settings.token);

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, isConfigured }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider');
  return ctx;
}