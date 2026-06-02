import { useState, useEffect } from 'react';
import Header from '../components/Header';
import PageContainer from '../components/PageContainer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { getInbox } from '../lib/api';
import type { InboxItem } from '../lib/types';

export default function InboxPage() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    getInbox()
      .then((res) => {
        if (res.success) setItems(res.items);
        else setError('Failed to load inbox');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Header title="Inbox" />
      <PageContainer>
        {loading && <LoadingSpinner />}
        {error && <ErrorMessage message={error} />}
        {!loading && !error && items.length === 0 && (
          <div className="text-center text-text-muted">Inbox is empty</div>
        )}
        {!loading && !error && items.length > 0 && (
          <div className="flex flex-col gap-2">
            {items.map((item) => (
              <div key={item.file} className="rounded-lg border border-border bg-card p-3">
                <div className="text-sm font-medium text-text">{item.title || 'Untitled'}</div>
                <div className="mt-1 flex items-center gap-2 text-xs text-text-muted">
                  <span>{item.source}</span>
                  <span>·</span>
                  <span>{item.suggested_action}</span>
                </div>
                <div className="mt-1 text-xs text-text-muted">{item.file}</div>
              </div>
            ))}
          </div>
        )}
      </PageContainer>
    </>
  );
}