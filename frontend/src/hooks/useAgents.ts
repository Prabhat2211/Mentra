import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Agent {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  model: string;
  tools_json: string;
  channel: string;
  memory_enabled: number;
  guardrails: string;
  personality: string;
  llm_provider?: string;
  llm_model?: string;
  created_at: string;
}

export function useAgents() {
  return useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => apiClient.get('/agents/').then(res => res.data),
    staleTime: 10000,
  });
}
