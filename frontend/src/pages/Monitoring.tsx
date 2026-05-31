import { useLogs } from '../hooks/useLogs';
import EmptyState from '../components/EmptyState';

const levelColors: Record<string, string> = {
  info: 'bg-blue-100 text-blue-800',
  error: 'bg-red-100 text-red-800',
  warn: 'bg-yellow-100 text-yellow-800',
  debug: 'bg-gray-100 text-gray-800',
};

export default function Monitoring() {
  const { data: logs = [], isLoading } = useLogs();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Monitoring</h2>
        <span className="text-sm text-gray-500">{logs.length} log entries</span>
      </div>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Level</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Event</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Run ID</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Details</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Time</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <EmptyState message="No logs yet. Run a workflow to see execution logs here." />
                </td>
              </tr>
            ) : (
              logs.map(log => {
                let payload: Record<string, unknown> = {};
                try { payload = JSON.parse(log.payload_json); } catch {}
                return (
                  <tr key={log.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs rounded-full capitalize ${levelColors[log.level] || levelColors.info}`}>
                        {log.level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">{log.event}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {log.run_id ? log.run_id.slice(0, 8) : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm max-w-xs truncate">
                      {payload.duration_ms ? (
                        <><span className="font-mono text-blue-600 font-medium">{payload.duration_ms as number}ms</span> {JSON.stringify(payload)}</>
                      ) : (
                        JSON.stringify(payload)
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
