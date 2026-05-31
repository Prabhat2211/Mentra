import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import { useWorkflows } from '../hooks/useWorkflows';
import EmptyState from '../components/EmptyState';
import FeedbackBanner from '../components/FeedbackBanner';

interface Workflow {
  id: string;
  name: string;
  description: string;
  template_key: string;
  config_json: string;
  is_custom: number;
  created_at: string;
}

interface RunResult {
  run_id: string;
  status: string;
  output: string;
  token_count: number;
  estimated_cost: number;
}

export default function Workflows() {
  const queryClient = useQueryClient();
  const { data: workflows = [], isLoading } = useWorkflows();
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [runInput, setRunInput] = useState('');
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const runMutation = useMutation({
    mutationFn: (data: { workflowId: string; userInput: string }) =>
      apiClient.post(`/workflows/${data.workflowId}/run`, {
        user_input: data.userInput,
        source_channel: 'ui',
      }),
    onSuccess: (res) => {
      setRunResult(res.data);
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['messages'] });
      queryClient.invalidateQueries({ queryKey: ['logs'] });
      showFeedback('success', 'Workflow completed');
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Run failed';
      showFeedback('error', typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (workflowId: string) => apiClient.delete(`/workflows/${workflowId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      if (selectedWorkflow && !workflows?.find(w => w.id === selectedWorkflow.id)) {
        setSelectedWorkflow(null);
      }
      showFeedback('success', 'Workflow deleted');
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to delete workflow';
      showFeedback('error', typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleRun = () => {
    if (!selectedWorkflow || !runInput.trim()) return;
    setRunResult(null);
    runMutation.mutate({ workflowId: selectedWorkflow.id, userInput: runInput });
  };

  const parseConfig = (wf: Workflow) => {
    try { return JSON.parse(wf.config_json || '{}'); } catch { return {}; }
  };

  const getAssignedAgentCount = (wf: Workflow) => {
    return Object.keys(parseConfig(wf).agent_assignments || {}).length;
  };

  const handleSelect = (wf: Workflow) => {
    if (selectedWorkflow?.id === wf.id) return;
    setSelectedWorkflow(wf);
    setRunInput('');
    setRunResult(null);
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Workflows</h2>
        <Link to="/workflows/new" className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm">
          + Create Workflow
        </Link>
      </div>

      {feedback && <FeedbackBanner type={feedback.type} message={feedback.message} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Available Workflows</h3>
            {workflows.length === 0 ? (
              <EmptyState message="No workflows created yet." action={
                <Link to="/workflows/new" className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm">
                  Create your first workflow
                </Link>
              } />
            ) : (
              <div className="space-y-2">
                {workflows.map((workflow) => {
                  const assigned = getAssignedAgentCount(workflow);
                  const isSelected = selectedWorkflow?.id === workflow.id;
                  return (
                    <div
                      key={workflow.id}
                      className={`rounded-lg border transition-colors ${
                        isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <button
                        onClick={() => handleSelect(workflow)}
                        className="w-full text-left p-3"
                      >
                        <p className="font-medium">{workflow.name}</p>
                        <p className="text-sm text-gray-500">{workflow.description}</p>
                        <div className="flex gap-2 mt-1">
                          <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800">
                            {workflow.template_key}
                          </span>
                          {assigned > 0 && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800">
                              {assigned} agents assigned
                            </span>
                          )}
                          {assigned === 0 && workflow.is_custom === 0 && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800">
                              No agents assigned
                            </span>
                          )}
                          {workflow.is_custom === 1 && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                              Custom
                            </span>
                          )}
                        </div>
                      </button>
                      {isSelected && (
                        <div className="flex gap-2 px-3 pb-3 border-t pt-2 mt-0">
                          {workflow.is_custom === 1 ? (
                            <Link
                              to="/builder"
                              className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-100 rounded"
                            >
                              Edit Flow
                            </Link>
                          ) : (
                            <Link
                              to={`/workflows/new`}
                              className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-100 rounded"
                            >
                              Edit Assignments
                            </Link>
                          )}
                          <button
                            onClick={() => {
                              if (confirm(`Delete workflow "${workflow.name}"?`)) {
                                deleteMutation.mutate(workflow.id);
                              }
                            }}
                            className="px-3 py-1 text-sm text-red-600 hover:bg-red-100 rounded"
                            disabled={deleteMutation.isPending}
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div>
          {selectedWorkflow && (
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h3 className="text-lg font-semibold mb-4">
                Run: {selectedWorkflow.name}
              </h3>

              {getAssignedAgentCount(selectedWorkflow) === 0 && selectedWorkflow.is_custom === 0 && (
                <div className="mb-4 p-3 bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-lg text-sm">
                  No agents assigned to this workflow. It will use default built-in agents.
                  <Link to="/workflows/new" className="block mt-1 text-blue-600 hover:underline">
                    Create a new workflow with agent assignments →
                  </Link>
                </div>
              )}

              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Input</label>
                <textarea
                  value={runInput}
                  onChange={(e) => setRunInput(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg"
                  rows={3}
                  placeholder="Enter your input..."
                />
              </div>
              <button
                onClick={handleRun}
                disabled={runMutation.isPending || !runInput.trim()}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {runMutation.isPending ? 'Running...' : 'Run Workflow'}
              </button>
            </div>
          )}

          {runResult && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Result</h3>
                <span className={`px-2 py-1 text-xs rounded-full ${runResult.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {runResult.status}
                </span>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-500 mb-1">Output</label>
                <div className="p-3 bg-gray-50 rounded-lg whitespace-pre-wrap text-sm">{runResult.output}</div>
              </div>
              <div className="flex gap-4 text-sm text-gray-500">
                <span>Tokens: {runResult.token_count}</span>
                <span>Est. Cost: ${runResult.estimated_cost.toFixed(4)}</span>
                <span>Run ID: {runResult.run_id.slice(0, 8)}...</span>
                {(runResult as any).duration_ms && <span>Runtime: {(runResult as any).duration_ms}ms</span>}
              </div>
            </div>
          )}

          {!selectedWorkflow && (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
              <p>Select a workflow to run it</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
