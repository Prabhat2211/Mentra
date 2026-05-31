import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Run {
  id: string;
  workflow_id: string;
  status: string;
  input: string;
  output: string;
  token_count: number;
  estimated_cost: number;
  created_at: string;
  completed_at?: string;
}

export function useRuns() {
  return useQuery<Run[]>({
    queryKey: ['runs'],
    queryFn: () => apiClient.get('/runs/').then(res => res.data),
    staleTime: 10000,
  });
}
