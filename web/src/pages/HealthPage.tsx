import { useState, useEffect } from 'react';
import Header from '../components/Header';
import PageContainer from '../components/PageContainer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { getHealth, getMetrics } from '../lib/api';
import type { HealthResponse, MetricsResponse, JobStatus } from '../lib/types';

function formatDuration(seconds?: number): string {
  if (!seconds) return '-';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-400';
  if (score >= 70) return 'text-lime-400';
  if (score >= 50) return 'text-yellow-400';
  if (score >= 30) return 'text-orange-400';
  return 'text-red-400';
}

function JobCard({ name, job }: { name: string; job?: JobStatus }) {
  const statusColors: Record<string, string> = {
    success: 'text-green-400',
    failure: 'text-red-400',
    running: 'text-yellow-400',
    unknown: 'text-gray-400',
  };
  const statusLabels: Record<string, string> = {
    success: '成功',
    failure: '失败',
    running: '运行中',
    unknown: '未知',
  };
  const status = job?.status || 'unknown';
  const color = statusColors[status] || 'text-gray-400';
  const label = statusLabels[status] || status;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-text">{name.toUpperCase()}</span>
        <span className={`text-sm font-bold ${color}`}>{label}</span>
      </div>
      {job?.date && job?.time && (
        <div className="text-xs text-text-muted">
          上次运行: {job.date} {job.time}
        </div>
      )}
      {job?.duration_seconds !== undefined && (
        <div className="text-xs text-text-muted">
          耗时: {formatDuration(job.duration_seconds)}
        </div>
      )}
      {job?.steps && job.steps.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {job.steps.map((step: { name: string; status: string; error?: string }, i: number) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="text-text-muted">{step.name}</span>
              <span className={step.status === 'success' ? 'text-green-400' : step.status === 'failure' ? 'text-red-400' : 'text-gray-400'}>
                {step.status === 'success' ? '✓' : step.status === 'failure' ? '✗' : '...'}
              </span>
            </div>
          ))}
        </div>
      )}
      {job?.error && (
        <div className="mt-2 text-xs text-red-400 truncate">
          错误: {job.error}
        </div>
      )}
    </div>
  );
}

function MetricsCard({ metrics }: { metrics: MetricsResponse }) {
  const scoreColor = getScoreColor(metrics.health_score);

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 text-sm font-medium text-text">Vault 健康评分</div>
      <div className="flex items-end gap-3">
        <div className={`text-4xl font-bold ${scoreColor}`}>
          {metrics.health_score}
        </div>
        <div className="text-lg text-text-muted mb-1">/100</div>
        <div className={`text-sm font-medium ${scoreColor} mb-2`}>
          ({metrics.health_grade})
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="flex justify-between">
          <span className="text-text-muted">笔记总量</span>
          <span className="text-text">{metrics.total_notes}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Atomic</span>
          <span className="text-text">{metrics.atomic_notes_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Inbox 积压</span>
          <span className={metrics.inbox_count > 10 ? 'text-yellow-400' : 'text-text'}>
            {metrics.inbox_count}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">孤岛笔记</span>
          <span className={metrics.orphan_notes > 0 ? 'text-yellow-400' : 'text-text'}>
            {metrics.orphan_notes}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">向量化</span>
          <span className="text-text">{metrics.vectorized_notes}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">链接数</span>
          <span className="text-text">{metrics.total_links}</span>
        </div>
      </div>
    </div>
  );
}

export default function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');

    getHealth()
      .then((h) => {
        if (h.status === 'ok') {
          setHealth(h);
        }
      })
      .catch(() => {
        // ignore health errors
      });

    getMetrics()
      .then((m) => {
        if (m && m.success !== false) {
          setMetrics(m);
        }
      })
      .catch(() => {
        // ignore metrics errors
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Header title="Health" />
      <PageContainer>
        {loading && <LoadingSpinner />}
        {error && <ErrorMessage message={error} />}
        {!loading && !error && health && (
          <div className="flex flex-col gap-4">
            {metrics && metrics.success !== false && (
              <MetricsCard metrics={metrics} />
            )}

            <div className="rounded-lg border border-border bg-card p-4">
              <div className="text-sm text-text-muted">System Status</div>
              <div className={`text-2xl font-bold ${health.status === 'ok' ? 'text-green-400' : 'text-red-400'}`}>
                {health.status}
              </div>
              <div className="mt-1 text-xs text-text-muted">
                {health.timestamp}
              </div>
            </div>

            {health.jobs && (
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-3 text-sm font-medium text-text">定时任务</div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <JobCard name="daily" job={health.jobs['daily']} />
                  <JobCard name="weekly" job={health.jobs['weekly']} />
                  <JobCard name="sync" job={health.jobs['sync']} />
                </div>
              </div>
            )}

            {health.scripts && (
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-2 text-sm font-medium text-text">Scripts</div>
                <div className="flex flex-col gap-1">
                  {Object.entries(health.scripts).map(([name, ok]) => (
                    <div key={name} className="flex items-center justify-between text-sm">
                      <span className="text-text-muted">{name}</span>
                      <span className={ok ? 'text-green-400' : 'text-red-400'}>
                        {ok ? '✓' : '✗'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {health.indexes && (
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-2 text-sm font-medium text-text">Indexes</div>
                <div className="flex flex-col gap-1">
                  {Object.entries(health.indexes).map(([name, ok]) => (
                    <div key={name} className="flex items-center justify-between text-sm">
                      <span className="text-text-muted">{name}</span>
                      <span className={ok ? 'text-green-400' : 'text-red-400'}>
                        {ok ? '✓' : '✗'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </PageContainer>
    </>
  );
}