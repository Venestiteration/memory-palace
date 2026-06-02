import { useState } from 'react';
import Header from '../components/Header';
import PageContainer from '../components/PageContainer';
import ErrorMessage from '../components/ErrorMessage';
import { captureText } from '../lib/api';

export default function CapturePage() {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await captureText({ content: content.trim() });
      if (res.success) {
        setSuccess('Captured!');
        setContent('');
      } else {
        setError(res.error || 'Failed to capture');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="Capture" />
      <PageContainer>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="What's on your mind?"
            className="min-h-40 w-full resize-none rounded-lg border border-border bg-card p-4 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
            disabled={loading}
          />
          {error && <ErrorMessage message={error} />}
          {success && (
            <div className="rounded-lg border border-green-900 bg-green-950/50 p-4 text-green-400">
              {success}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !content.trim()}
            className="w-full rounded-lg bg-accent py-3 font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save to Inbox'}
          </button>
        </form>
      </PageContainer>
    </>
  );
}