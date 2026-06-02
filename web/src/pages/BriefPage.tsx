import { useState, useEffect } from 'react';
import Header from '../components/Header';
import PageContainer from '../components/PageContainer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { getDailyBrief, getWeeklyBrief } from '../lib/api';
import type { BriefResponse } from '../lib/types';

type Tab = 'daily' | 'weekly';

export default function BriefPage() {
  const [tab, setTab] = useState<Tab>('daily');
  const [loading, setLoading] = useState(true);
  const [brief, setBrief] = useState<BriefResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    setBrief(null);
    const fetch_ = tab === 'daily' ? getDailyBrief() : getWeeklyBrief();
    fetch_
      .then((res) => {
        setBrief(res);
        if (!res.success) setError(res.error || 'Failed to load brief');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [tab]);

  return (
    <>
      <Header title="Brief" />
      <PageContainer className="flex flex-col gap-4">
        <div className="flex rounded-lg border border-border p-1">
          <button
            onClick={() => setTab('daily')}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
              tab === 'daily' ? 'bg-accent text-white' : 'text-text-muted'
            }`}
          >
            Daily
          </button>
          <button
            onClick={() => setTab('weekly')}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
              tab === 'weekly' ? 'bg-accent text-white' : 'text-text-muted'
            }`}
          >
            Weekly
          </button>
        </div>

        {loading && <LoadingSpinner />}
        {error && <ErrorMessage message={error} />}

        {brief?.content && (
          <div className="rounded-lg border border-border bg-card p-4">
            <pre className="whitespace-pre-wrap text-sm text-text">
              {brief.content}
            </pre>
          </div>
        )}

        {!loading && !brief?.content && !error && (
          <div className="text-center text-text-muted">
            No brief available. Generate one first.
          </div>
        )}
      </PageContainer>
    </>
  );
}