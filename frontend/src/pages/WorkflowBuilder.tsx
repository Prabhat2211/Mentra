import { useCallback, useState } from 'react';
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Connection,
  type Node,
} from 'reactflow';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';

interface Agent {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  model: string;
  tools_json: string;
  channel: string;
  memory_enabled: number;
}

interface AgentNodeData {
  label: string;
  agentId: string;
  role: string;
}

const initialNodes: Node<AgentNodeData>[] = [
  {
    id: 'start',
    type: 'input',
    data: { label: 'Start', agentId: '', role: '' },
    position: { x: 250, y: 50 },
  },
  {
    id: 'end',
    type: 'output',
    data: { label: 'End', agentId: '', role: '' },
    position: { x: 250, y: 400 },
  },
];

const defaultEdgeOptions = {
  animated: true,
  style: { stroke: '#3b82f6' },
  markerEnd: { type: MarkerType.ArrowClosed },
};

export default function WorkflowBuilder() {
  const queryClient = useQueryClient();
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => apiClient.get('/agents/').then((res) => res.data),
  });

  const createWorkflowMutation = useMutation({
    mutationFn: (data: {
      name: string;
      description: string;
      nodes: Record<string, unknown>[];
      edges: Record<string, unknown>[];
    }) =>
      apiClient.post('/workflows/', {
        name: data.name,
        description: data.description,
        template_key: 'custom',
        is_custom: true,
        nodes: data.nodes,
        edges: data.edges,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      setWorkflowName('');
      setWorkflowDescription('');
    },
  });

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const agentData = event.dataTransfer.getData('application/agent');
      if (!agentData) return;

      const agent: Agent = JSON.parse(agentData);
      const position = { x: event.clientX - 350, y: event.clientY - 150 };

      const newNode: Node<AgentNodeData> = {
        id: `agent-${agent.id}-${Date.now()}`,
        type: 'default',
        position,
        data: { label: agent.name, agentId: agent.id, role: agent.role },
        style: {
          background: '#eff6ff',
          border: '2px solid #3b82f6',
          borderRadius: '8px',
          padding: '10px 20px',
          fontSize: '14px',
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes]
  );

  const handleSave = () => {
    const workflowNodes = nodes
      .filter((n) => n.id !== 'start' && n.id !== 'end')
      .map((n) => ({
        id: n.id,
        agent_id: n.data.agentId,
        label: n.data.label,
        position: n.position,
      }));

    const workflowEdges = edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
    }));

    createWorkflowMutation.mutate({
      name: workflowName || 'Untitled Workflow',
      description: workflowDescription || 'Custom drag-and-drop workflow',
      nodes: workflowNodes,
      edges: workflowEdges,
    });
  };

  const handleReset = () => {
    setNodes(initialNodes);
    setEdges([]);
    setWorkflowName('');
    setWorkflowDescription('');
  };

  const onDragStart = (event: React.DragEvent, agent: Agent) => {
    event.dataTransfer.setData('application/agent', JSON.stringify(agent));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Workflow Builder</h2>

      <div className="flex gap-4" style={{ height: 'calc(100vh - 200px)' }}>
        {/* Left Sidebar - Agent Palette */}
        <div className="w-64 bg-white rounded-lg shadow p-4 overflow-auto flex-shrink-0">
          <h3 className="text-lg font-semibold mb-4">Agents</h3>
          <p className="text-sm text-gray-500 mb-4">Drag agents onto the canvas</p>
          {agents.length === 0 ? (
            <p className="text-sm text-gray-400">No agents created yet</p>
          ) : (
            <div className="space-y-2">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  draggable
                  onDragStart={(e) => onDragStart(e, agent)}
                  className="p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-grab active:cursor-grabbing hover:bg-blue-100 transition-colors"
                >
                  <p className="font-medium text-sm">{agent.name}</p>
                  <p className="text-xs text-gray-500">{agent.role}</p>
                </div>
              ))}
            </div>
          )}

          <div className="mt-8">
            <h3 className="text-lg font-semibold mb-4">Workflow Info</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="My Workflow"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={workflowDescription}
                  onChange={(e) => setWorkflowDescription(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  rows={2}
                  placeholder="Describe this workflow..."
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={handleSave}
                  disabled={createWorkflowMutation.isPending}
                  className="flex-1 px-3 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 disabled:opacity-50"
                >
                  {createWorkflowMutation.isPending ? 'Saving...' : 'Save Workflow'}
                </button>
                <button
                  onClick={handleReset}
                  className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300"
                >
                  Reset
                </button>
              </div>
              {createWorkflowMutation.isSuccess && (
                <p className="text-sm text-green-600">Workflow saved successfully!</p>
              )}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDragOver={onDragOver}
            onDrop={onDrop}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
            attributionPosition="bottom-left"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
