import { useAgents } from '../hooks/useAgents';
import { useWorkflows } from '../hooks/useWorkflows';
import { useRuns } from '../hooks/useRuns';
import { useMetrics } from '../hooks/useMetrics';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import MetricCard from '../components/MetricCard';
import Skeleton from '../components/Skeleton';

export default function Dashboard() {
  const { data: agents = [], isLoading: agentsLoading } = useAgents();
  const { data: workflows = [], isLoading: workflowsLoading } = useWorkflows();
  const { data: runs = [], isLoading: runsLoading } = useRuns();
  const { data: metrics, isLoading: metricsLoading } = useMetrics();

  const { data: llmStatus, isLoading: llmLoading } = useQuery<{ provider: string; model: string; mode: string; configured: boolean }>({
    queryKey: ['llm-status'],
    queryFn: () => apiClient.get('/llm-status').then(res => res.data),
    staleTime: 30000,
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* System Status */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard label="Agents" value={agentsLoading ? '...' : agents.length} />
        <MetricCard label="Workflows" value={workflowsLoading ? '...' : workflows.length} />
        <MetricCard label="Runs" value={runsLoading ? '...' : runs.length} />
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm text-gray-500">LLM Mode</h3>
          {llmLoading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <>
              <p className="text-2xl font-bold capitalize">{llmStatus?.mode || 'Unknown'}</p>
              {llmStatus?.configured ? (
                <p className="text-xs text-green-600">{llmStatus.provider} / {llmStatus.model}</p>
              ) : (
                <p className="text-xs text-orange-600">Not configured</p>
              )}
            </>
          )}
        </div>
      </div>

      {/* Impact Metrics */}
      <h3 className="text-lg font-semibold mb-4">Impact Metrics</h3>
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard
          label="Configurable Dimensions"
          value={metricsLoading ? '...' : metrics?.configurable_dimensions_per_agent ?? '-'}
          sub="per agent"
        />
        <MetricCard
          label="Task Completion Rate"
          value={metricsLoading ? '...' : `${metrics?.completion_rate ?? '-'}%`}
          sub={metrics ? `${metrics.completed_runs}/${metrics.total_runs} runs` : ''}
        />
        <MetricCard
          label="Avg Runtime"
          value={metricsLoading ? '...' : metrics?.avg_runtime_ms ? `${metrics.avg_runtime_ms}ms` : '-'}
          sub="per workflow"
        />
        <MetricCard
          label="Total Runtime"
          value={metricsLoading ? '...' : metrics?.total_runtime_ms ? `${metrics.total_runtime_ms}ms` : '-'}
          sub={metrics ? `across ${metrics.total_runs} run(s)` : ''}
        />
      </div>
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard
          label="Agent Messages"
          value={metricsLoading ? '...' : metrics?.total_agent_messages ?? '-'}
          sub="persisted across all runs"
        />
        <MetricCard
          label="Failed Runs"
          value={metricsLoading ? '...' : metrics?.failed_runs ?? 0}
          sub={metrics?.total_runs ? `${((metrics.failed_runs / metrics.total_runs) * 100).toFixed(1)}% failure rate` : ''}
        />
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Recent Agents</h3>
          {agentsLoading ? (
            <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
          ) : agents.length === 0 ? (
            <p className="text-gray-500">No agents created yet</p>
          ) : (
            agents.slice(0, 5).map(agent => (
              <div key={agent.id} className="border-b py-2">
                <p className="font-medium">{agent.name}</p>
                <p className="text-sm text-gray-500">{agent.role}</p>
              </div>
            ))
          )}
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Recent Workflows</h3>
          {workflowsLoading ? (
            <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
          ) : workflows.length === 0 ? (
            <p className="text-gray-500">No workflows created yet</p>
          ) : (
            workflows.map(wf => (
              <div key={wf.id} className="border-b py-2">
                <p className="font-medium">{wf.name}</p>
                <p className="text-sm text-gray-500">{wf.template_key}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
