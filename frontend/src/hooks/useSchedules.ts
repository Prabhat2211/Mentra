import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Schedule {
  id: string;
  workflow_id: string;
  name: string;
  interval_minutes: number;
  input_text: string;
  enabled: number;
  created_at: string;
  last_run_at: string | null;
}

export function useSchedules() {
  return useQuery<Schedule[]>({
    queryKey: ['schedules'],
    queryFn: () => apiClient.get('/schedules/').then(res => res.data),
    refetchInterval: 10000,
  });
}
