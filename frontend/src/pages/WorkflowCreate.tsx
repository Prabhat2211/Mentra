import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import { useAgents } from '../hooks/useAgents';
import FeedbackBanner from '../components/FeedbackBanner';

const TEMPLATES = [
  {
    key: 'research_summary',
    name: 'Research Summary',
    description: 'Two-agent workflow that gathers structured notes and turns them into a concise answer.',
    nodes: ['research_agent', 'summarizer_agent'],
    nodeLabels: {
      research_agent: 'Research Agent',
      summarizer_agent: 'Summarizer Agent',
    },
    nodeDescriptions: {
      research_agent: 'Collects key facts and produces structured notes from the user input.',
      summarizer_agent: 'Writes a concise final answer from the research notes.',
    },
    sampleInput: 'Summarize the main benefits and risks of using AI agents in customer support.',
  },
  {
    key: 'financial_assistant',
    name: 'Financial Assistant',
    description: 'Detects stock queries, resolves tickers, fetches Yahoo Finance data, and formats a clean reply.',
    nodes: [
      'query_detector_agent',
      'company_extractor_agent',
      'ticker_resolver_agent',
      'market_data_agent',
      'response_formatter_agent',
    ],
    nodeLabels: {
      query_detector_agent: 'Query Detector',
      company_extractor_agent: 'Company Extractor',
      ticker_resolver_agent: 'Ticker Resolver',
      market_data_agent: 'Market Data Fetcher',
      response_formatter_agent: 'Response Formatter',
    },
    nodeDescriptions: {
      query_detector_agent: 'Detects whether a message is a stock-related query.',
      company_extractor_agent: 'Extracts the company name or ticker mentioned by the user.',
      ticker_resolver_agent: 'Resolves the extracted company or ticker to the exact stock symbol.',
      market_data_agent: 'Fetches latest stock price and key stats from Yahoo Finance.',
      response_formatter_agent: 'Formats a clean response with a short disclaimer.',
    },
    sampleInput: "What is Apple's stock price today?",
  },
];

export default function WorkflowCreate() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: agents = [], isLoading: agentsLoading } = useAgents();

  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const template = TEMPLATES.find(t => t.key === selectedTemplate);

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string; template_key: string; agent_assignments: Record<string, string> }) =>
      apiClient.post('/workflows/', data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      setFeedback({ type: 'success', message: `Workflow created (${(res.data as any).id?.slice(0, 8)}...)` });
      setTimeout(() => navigate('/workflows'), 1500);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to create workflow';
      setFeedback({ type: 'error', message: typeof msg === 'string' ? msg : JSON.stringify(msg) });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate || !workflowName.trim()) return;
    const filteredAssignments: Record<string, string> = {};
    for (const [node, agentId] of Object.entries(assignments)) {
      if (agentId) filteredAssignments[node] = agentId;
    }
    const tmpl = TEMPLATES.find(t => t.key === selectedTemplate);
    createMutation.mutate({
      name: workflowName,
      description: tmpl?.description || '',
      template_key: selectedTemplate,
      agent_assignments: Object.keys(filteredAssignments).length > 0 ? filteredAssignments : {},
    });
  };

  const allAssigned = template
    ? template.nodes.every(n => assignments[n])
    : false;

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/workflows')} className="text-gray-500 hover:text-gray-700">
          &larr; Back
        </button>
        <h2 className="text-2xl font-bold">Create Workflow</h2>
      </div>

      {feedback && <FeedbackBanner type={feedback.type} message={feedback.message} />}

      <form onSubmit={handleSubmit}>
        {/* Step 1: Pick Template */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">1. Choose a Template</h3>
          <div className="grid grid-cols-2 gap-4">
            {TEMPLATES.map(t => (
              <button
                key={t.key}
                type="button"
                onClick={() => {
                  setSelectedTemplate(t.key);
                  setAssignments({});
                  setWorkflowName(t.name);
                }}
                className={`text-left p-4 rounded-lg border transition-colors ${
                  selectedTemplate === t.key
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <p className="font-semibold text-base">{t.name}</p>
                <p className="text-sm text-gray-500 mt-1">{t.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {t.nodes.map(n => (
                    <span key={n} className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700">
                      {t.nodeLabels[n]}
                    </span>
                  ))}
                </div>
              </button>
            ))}
            <button
              type="button"
              onClick={() => navigate('/builder')}
              className="text-left p-4 rounded-lg border-2 border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50 transition-colors flex flex-col items-center justify-center"
            >
              <p className="font-semibold text-base text-blue-600">Custom Drag-and-Drop</p>
              <p className="text-sm text-gray-500 mt-1">Build a workflow from scratch by dragging agents onto a canvas</p>
              <span className="mt-2 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                React Flow Canvas
              </span>
            </button>
          </div>
        </div>

        {template && (
          <>
            {/* Step 2: Name */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h3 className="text-lg font-semibold mb-4">2. Name Your Workflow</h3>
              <input
                type="text"
                value={workflowName}
                onChange={e => setWorkflowName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="My Workflow"
                required
              />
            </div>

            {/* Step 3: Assign Agents */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h3 className="text-lg font-semibold mb-4">3. Assign Agents to Roles</h3>
              <p className="text-sm text-gray-500 mb-4">
                Pick which agent handles each step in the workflow. Agents without assignment will use the default built-in logic.
              </p>

              {agentsLoading ? (
                <div className="text-sm text-gray-500">Loading agents...</div>
              ) : agents.length === 0 ? (
                <div className="p-4 bg-yellow-50 text-yellow-800 rounded-lg text-sm mb-4">
                  No agents created yet.{' '}
                  <button
                    type="button"
                    onClick={() => navigate('/agents')}
                    className="text-blue-600 hover:underline"
                  >
                    Create agents first
                  </button>
                </div>
              ) : null}

              <div className="space-y-4">
                {template.nodes.map(node => (
                  <div key={node} className="p-4 border rounded-lg">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-medium">{template.nodeLabels[node]}</p>
                        <p className="text-sm text-gray-500">{template.nodeDescriptions[node]}</p>
                      </div>
                    </div>
                    <select
                      value={assignments[node] || ''}
                      onChange={e =>
                        setAssignments(prev => ({ ...prev, [node]: e.target.value }))
                      }
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                    >
                      <option value="">Use default (built-in agent)</option>
                      {agents.map(agent => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name} ({agent.role})
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>

            {/* Submit */}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={createMutation.isPending || !workflowName.trim()}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : allAssigned ? 'Create Workflow' : 'Create Workflow (with defaults)'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/workflows')}
                className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
