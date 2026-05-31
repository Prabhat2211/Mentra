import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Metrics {
  agents_count: number;
  workflows_count: number;
  configurable_dimensions_per_agent: number;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  completion_rate: number;
  total_agent_messages: number;
  total_messages: number;
  avg_runtime_ms: number;
  total_runtime_ms: number;
}

export function useMetrics() {
  return useQuery<Metrics>({
    queryKey: ['metrics'],
    queryFn: () => apiClient.get('/metrics').then(res => res.data),
    refetchInterval: 10000,
  });
}
