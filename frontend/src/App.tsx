import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactFlowProvider } from 'reactflow';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AgentBuilder from './pages/AgentBuilder';
import Workflows from './pages/Workflows';
import WorkflowCreate from './pages/WorkflowCreate';
import WorkflowBuilder from './pages/WorkflowBuilder';
import Messages from './pages/Messages';
import Monitoring from './pages/Monitoring';
import Schedules from './pages/Schedules';
import Help from './pages/Help';
import 'reactflow/dist/style.css';
import './index.css';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ReactFlowProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/agents" element={<AgentBuilder />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/workflows/new" element={<WorkflowCreate />} />
              <Route path="/builder" element={<WorkflowBuilder />} />
              <Route path="/messages" element={<Messages />} />
              <Route path="/schedules" element={<Schedules />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/help" element={<Help />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ReactFlowProvider>
    </QueryClientProvider>
  );
}

export default App;
