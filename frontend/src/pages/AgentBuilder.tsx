import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import { useAgents } from '../hooks/useAgents';
import type { Agent } from '../hooks/useAgents';
import FeedbackBanner from '../components/FeedbackBanner';

interface AgentFormData {
  name: string;
  role: string;
  system_prompt: string;
  model: string;
  tools: string[];
  channel: string;
  memory_enabled: boolean;
  guardrails: string;
  personality: string;
  llm_provider: string;
  llm_api_key: string;
  llm_model: string;
}

const AVAILABLE_TOOLS = ['web_search_stub', 'save_note', 'get_stock_quote'];

const PERSONALITY_OPTIONS = [
  { value: 'professional', label: 'Professional' },
  { value: 'polite', label: 'Polite' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'casual', label: 'Casual' },
  { value: 'formal', label: 'Formal' },
  { value: 'sarcastic', label: 'Sarcastic' },
  { value: 'rude', label: 'Rude' },
];

const emptyForm: AgentFormData = {
  name: '', role: '', system_prompt: '', model: 'gpt-4o-mini', tools: [],
  channel: 'ui', memory_enabled: false, guardrails: '', personality: 'professional',
  llm_provider: 'use_global', llm_api_key: '', llm_model: '',
};

export default function AgentBuilder() {
  const queryClient = useQueryClient();
  const { data: agents = [], isLoading } = useAgents();
  const [showForm, setShowForm] = useState(false);
  const [editingAgent, setEditingAgent] = useState<string | null>(null);
  const [formData, setFormData] = useState<AgentFormData>(emptyForm);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const createMutation = useMutation({
    mutationFn: (data: AgentFormData) =>
      apiClient.post('/agents/', { ...data, tools: data.tools }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setFormData(emptyForm);
      setShowForm(false);
      showFeedback('success', `Agent created (${(res.data as any).id?.slice(0, 8)}...)`);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to create agent';
      showFeedback('error', typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: string; form: AgentFormData }) =>
      apiClient.put(`/agents/${data.id}`, { ...data.form, tools: data.form.tools }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setFormData(emptyForm);
      setEditingAgent(null);
      setShowForm(false);
      showFeedback('success', 'Agent updated');
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to update agent';
      showFeedback('error', typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (agentId: string) => apiClient.delete(`/agents/${agentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      if (editingAgent) { setEditingAgent(null); setShowForm(false); setFormData(emptyForm); }
      showFeedback('success', 'Agent deleted');
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to delete agent';
      showFeedback('error', typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const startCreate = () => { setFormData(emptyForm); setEditingAgent(null); setShowForm(true); };

  const startEdit = (agent: Agent) => {
    let tools: string[] = [];
    try { tools = JSON.parse(agent.tools_json || '[]'); } catch {}
    setFormData({
      name: agent.name, role: agent.role, system_prompt: agent.system_prompt,
      model: agent.model, tools, channel: agent.channel,
      memory_enabled: agent.memory_enabled === 1, guardrails: agent.guardrails || '',
      personality: agent.personality || 'professional',
      llm_provider: agent.llm_provider || 'use_global', llm_api_key: '', llm_model: agent.llm_model || '',
    });
    setEditingAgent(agent.id);
    setShowForm(true);
  };

  const cancelForm = () => { setFormData(emptyForm); setEditingAgent(null); setShowForm(false); };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingAgent) updateMutation.mutate({ id: editingAgent, form: formData });
    else createMutation.mutate(formData);
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Agents</h2>
        {!showForm && (
          <button onClick={startCreate} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm">
            + Create Agent
          </button>
        )}
      </div>

      {feedback && <FeedbackBanner type={feedback.type} message={feedback.message} />}

      {/* Agent List */}
      <div className="bg-white rounded-lg shadow mb-6">
        <h3 className="text-lg font-semibold p-4 border-b">Existing Agents</h3>
        {agents.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            <p className="mb-3">No agents yet</p>
            <button onClick={startCreate} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm">
              Create your first agent
            </button>
          </div>
        ) : (
          <div className="divide-y">
            {agents.map(agent => (
              <div key={agent.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                <div className="flex-1">
                  <p className="font-medium">{agent.name}</p>
                  <p className="text-sm text-gray-500">{agent.role}</p>
                  <div className="flex gap-2 mt-1 flex-wrap">
                    <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800">{agent.model}</span>
                    <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800 capitalize">{agent.channel}</span>
                    <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800">{agent.personality || 'professional'}</span>
                    {agent.llm_provider && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800">{agent.llm_provider}</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  <button onClick={() => startEdit(agent)} className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded">Edit</button>
                  <button onClick={() => { if (confirm(`Delete "${agent.name}"?`)) deleteMutation.mutate(agent.id); }}
                    className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded" disabled={deleteMutation.isPending}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create / Edit Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">{editingAgent ? 'Edit Agent' : 'Create New Agent'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg" required />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <input type="text" value={formData.role} onChange={e => setFormData({ ...formData, role: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg" required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">System Prompt</label>
                <textarea value={formData.system_prompt} onChange={e => setFormData({ ...formData, system_prompt: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg" rows={3} required />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Model</label>
                <input type="text" value={formData.model} onChange={e => setFormData({ ...formData, model: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg" placeholder="gpt-4o-mini" />
              </div>
            </div>

            {/* Personality */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Personality / Tone</label>
              <select value={formData.personality} onChange={e => setFormData({ ...formData, personality: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg">
                {PERSONALITY_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* LLM Configuration */}
            <div className="border-t pt-4 mb-4">
              <h4 className="font-semibold mb-2">LLM Configuration</h4>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1">LLM Provider</label>
                  <select value={formData.llm_provider} onChange={e => setFormData({ ...formData, llm_provider: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg">
                    <option value="use_global">Use Global Config</option>
                    <option value="groq">Groq</option>
                    <option value="gemini">Gemini</option>
                    <option value="openai">OpenAI</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">API Key (Encrypted)</label>
                  <input type="password" value={formData.llm_api_key} onChange={e => setFormData({ ...formData, llm_api_key: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg" placeholder="Leave empty to use global" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Model Override</label>
                  <input type="text" value={formData.llm_model} onChange={e => setFormData({ ...formData, llm_model: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg" placeholder="e.g., gpt-oss-120B" />
                </div>
              </div>
            </div>

            {/* Tools */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Tools</label>
              <div className="flex gap-2">
                {AVAILABLE_TOOLS.map(tool => (
                  <label key={tool} className="flex items-center">
                    <input type="checkbox" checked={formData.tools.includes(tool)}
                      onChange={e => setFormData({ ...formData, tools: e.target.checked ? [...formData.tools, tool] : formData.tools.filter(t => t !== tool) })}
                      className="mr-1" />
                    {tool}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Channel</label>
                <select value={formData.channel} onChange={e => setFormData({ ...formData, channel: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg">
                  <option value="ui">UI</option>
                  <option value="telegram">Telegram</option>
                  <option value="agent">Agent</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Guardrails</label>
                <input type="text" value={formData.guardrails} onChange={e => setFormData({ ...formData, guardrails: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg" />
              </div>
            </div>

            <div className="flex items-center gap-4 mb-4">
              <label className="flex items-center">
                <input type="checkbox" checked={formData.memory_enabled}
                  onChange={e => setFormData({ ...formData, memory_enabled: e.target.checked })} className="mr-2" />
                Memory Enabled
              </label>
            </div>

            <div className="flex gap-2">
              <button type="submit"
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                disabled={createMutation.isPending || updateMutation.isPending}>
                {editingAgent ? (updateMutation.isPending ? 'Updating...' : 'Update Agent') : (createMutation.isPending ? 'Creating...' : 'Create Agent')}
              </button>
              <button type="button" onClick={cancelForm} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">Cancel</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
