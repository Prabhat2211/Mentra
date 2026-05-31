import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import { useSchedules } from '../hooks/useSchedules';
import { useWorkflows } from '../hooks/useWorkflows';
import FeedbackBanner from '../components/FeedbackBanner';

const INTERVAL_OPTIONS = [
  { value: 15, label: 'Every 15 minutes' },
  { value: 30, label: 'Every 30 minutes' },
  { value: 60, label: 'Every hour' },
  { value: 360, label: 'Every 6 hours' },
  { value: 720, label: 'Every 12 hours' },
  { value: 1440, label: 'Every day' },
  { value: 10080, label: 'Every week' },
];

export default function Schedules() {
  const queryClient = useQueryClient();
  const { data: schedules = [], isLoading } = useSchedules();
  const { data: workflows = [] } = useWorkflows();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [workflowId, setWorkflowId] = useState('');
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [inputText, setInputText] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const createMutation = useMutation({
    mutationFn: (data: { workflow_id: string; name: string; interval_minutes: number; input_text: string }) =>
      apiClient.post('/schedules/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      setShowForm(false);
      setName('');
      setWorkflowId('');
      setInputText('');
      showFeedback('success', 'Schedule created');
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Failed';
      showFeedback('error', typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/schedules/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      showFeedback('success', 'Schedule deleted');
    },
    onError: (err: any) => {
      showFeedback('error', err?.message || 'Delete failed');
    },
  });

  const intervalLabel = (min: number) => INTERVAL_OPTIONS.find(o => o.value === min)?.label || `${min} min`;

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Schedules</h2>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm">
            + Create Schedule
          </button>
        )}
      </div>

      {feedback && <FeedbackBanner type={feedback.type} message={feedback.message} />}

      {showForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">New Schedule</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full px-3 py-2 border rounded-lg" required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Workflow</label>
              <select value={workflowId} onChange={e => setWorkflowId(e.target.value)} className="w-full px-3 py-2 border rounded-lg" required>
                <option value="">Select a workflow...</option>
                {workflows.map(wf => (
                  <option key={wf.id} value={wf.id}>{wf.name} ({wf.template_key})</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Interval</label>
              <select value={intervalMinutes} onChange={e => setIntervalMinutes(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg">
                {INTERVAL_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Default Input (optional)</label>
              <input type="text" value={inputText} onChange={e => setInputText(e.target.value)} className="w-full px-3 py-2 border rounded-lg" placeholder="e.g. What's Apple's stock price?" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => createMutation.mutate({ workflow_id: workflowId, name, interval_minutes: intervalMinutes, input_text: inputText })}
              disabled={createMutation.isPending || !name || !workflowId}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50">
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        {schedules.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            <p>No schedules yet. Create one to run a workflow automatically.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Name</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Workflow</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Interval</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Last Run</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map(s => {
                const wf = workflows.find(w => w.id === s.workflow_id);
                return (
                  <tr key={s.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium">{s.name}</td>
                    <td className="px-4 py-3 text-sm">{wf?.name || s.workflow_id.slice(0, 8)}</td>
                    <td className="px-4 py-3 text-sm">{intervalLabel(s.interval_minutes)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs rounded-full ${s.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {s.enabled ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{s.last_run_at ? new Date(s.last_run_at).toLocaleString() : 'Never'}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => { if (confirm(`Delete schedule "${s.name}"?`)) deleteMutation.mutate(s.id); }}
                        className="px-2 py-1 text-sm text-red-600 hover:bg-red-50 rounded" disabled={deleteMutation.isPending}>Delete</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
