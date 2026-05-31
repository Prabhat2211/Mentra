import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Log {
  id: string;
  run_id: string | null;
  level: string;
  event: string;
  payload_json: string;
  created_at: string;
}

export function useLogs() {
  return useQuery<Log[]>({
    queryKey: ['logs'],
    queryFn: () => apiClient.get('/logs/').then(res => res.data),
    refetchInterval: 5000,
  });
}
