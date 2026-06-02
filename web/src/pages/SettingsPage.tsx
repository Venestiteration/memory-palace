import { useState } from 'react';
import { useSettings } from '../contexts/SettingsContext';
import Header from '../components/Header';
import PageContainer from '../components/PageContainer';

export default function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const [apiUrl, setApiUrl] = useState(settings.apiUrl);
  const [token, setToken] = useState(settings.token);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    updateSettings({ apiUrl, token });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <>
      <Header title="Settings" />
      <PageContainer>
        <div className="flex flex-col gap-4">
          <div className="rounded-lg border border-border bg-card p-4">
            <label className="block text-sm font-medium text-text">API Base URL</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://127.0.0.1:8000"
              className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div className="rounded-lg border border-border bg-card p-4">
            <label className="block text-sm font-medium text-text">API Token</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Bearer token (from MEMORY_PALACE_API_KEY)"
              className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
            />
            <p className="mt-2 text-xs text-text-muted">
              Token is stored locally in your browser. Get it from the backend environment variable MEMORY_PALACE_API_KEY.
            </p>
          </div>

          <button
            onClick={handleSave}
            className="rounded-lg bg-accent py-3 font-medium text-white transition-colors hover:bg-accent-hover"
          >
            Save Settings
          </button>

          {saved && (
            <div className="rounded-lg border border-green-900 bg-green-950/50 p-4 text-green-400 text-center">
              Settings saved
            </div>
          )}
        </div>
      </PageContainer>
    </>
  );
}