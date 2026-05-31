import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Workflow {
  id: string;
  name: string;
  description: string;
  template_key: string;
  config_json: string;
  is_custom: number;
  created_at: string;
}

export function useWorkflows() {
  return useQuery<Workflow[]>({
    queryKey: ['workflows'],
    queryFn: () => apiClient.get('/workflows/').then(res => res.data),
    staleTime: 10000,
  });
}
