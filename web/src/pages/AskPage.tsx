import { useState } from 'react';
import Header from '../components/Header';
import PageContainer from '../components/PageContainer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { ask } from '../lib/api';
import type { SearchResult } from '../lib/types';

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState('');
  const [references, setReferences] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError('');
    setAnswer('');
    setReferences([]);
    try {
      const res = await ask({ question, limit: 5 });
      if (res.success) {
        setAnswer(res.answer);
        setReferences(res.references);
      } else {
        setError('Failed to get answer');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="Ask" />
      <PageContainer className="flex flex-col gap-4">
        <form onSubmit={handleAsk} className="flex flex-col gap-2">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask your knowledge base..."
            className="min-h-20 w-full resize-none rounded-lg border border-border bg-card p-4 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="rounded-lg bg-accent py-2 font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </form>

        {loading && <LoadingSpinner />}

        {error && <ErrorMessage message={error} />}

        {answer && (
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="prose prose-invert prose-sm max-w-none">
              <div className="whitespace-pre-wrap text-text">{answer}</div>
            </div>
          </div>
        )}

        {references.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium text-text-muted">Sources</h3>
            {references.map((ref, i) => (
              <div
                key={i}
                className="rounded-lg border-l-4 border-accent bg-card p-3"
              >
                <div className="text-sm font-medium text-text">{ref.title}</div>
                {ref.snippet && (
                  <div className="mt-1 text-xs text-text-muted">
                    {ref.snippet}
                  </div>
                )}
                <div className="mt-1 text-xs text-text-muted">{ref.path}</div>
              </div>
            ))}
          </div>
        )}
      </PageContainer>
    </>
  );
}