import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

export interface Message {
  id: string;
  run_id: string | null;
  workflow_id: string;
  from_agent_id: string | null;
  to_agent_id: string | null;
  channel: string;
  content: string;
  metadata_json: string;
  created_at: string;
}

export function useMessages() {
  return useQuery<Message[]>({
    queryKey: ['messages'],
    queryFn: () => apiClient.get('/messages/').then(res => res.data),
    refetchInterval: 5000,
  });
}
