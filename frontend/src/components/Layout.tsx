import { NavLink, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '' },
  { path: '/agents', label: 'Agents', icon: '' },
  { path: '/workflows', label: 'Workflows', icon: '' },
  { path: '/builder', label: 'Builder', icon: '' },
  { path: '/schedules', label: 'Schedules', icon: '' },
  { path: '/messages', label: 'Messages', icon: '' },
  { path: '/monitoring', label: 'Monitoring', icon: '' },
  { path: '/help', label: 'Help', icon: '' },
];

export default function Layout() {
  const { data: llmStatus } = useQuery<{ provider: string; model: string; mode: string; configured: boolean }>({
    queryKey: ['llm-status'],
    queryFn: () => apiClient.get('/llm-status').then(res => res.data),
    staleTime: 30000,
  });

  return (
    <div className="flex h-screen">
      <div className="w-64 bg-white shadow-md flex-shrink-0 flex flex-col">
        <div className="p-4 border-b">
          <h1 className="text-xl font-bold text-gray-800">Yuno Agent Orchestration</h1>
        </div>
        <nav className="p-4 flex-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `block w-full text-left px-4 py-2 rounded-lg mb-2 capitalize ${
                  isActive ? 'bg-blue-500 text-white' : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        {llmStatus && (
          <div className="p-4 border-t text-xs text-gray-500">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${llmStatus.configured ? 'bg-green-500' : 'bg-orange-500'}`} />
              {llmStatus.mode} / {llmStatus.provider}
            </div>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto p-8 bg-gray-50">
        <Outlet />
      </div>
    </div>
  );
}
