import { useMessages } from '../hooks/useMessages';
import EmptyState from '../components/EmptyState';

export default function Messages() {
  const { data: messages = [], isLoading } = useMessages();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Messages</h2>
        <span className="text-sm text-gray-500">{messages.length} messages</span>
      </div>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Channel</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">From Agent</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">To Agent</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Content</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Time</th>
            </tr>
          </thead>
          <tbody>
            {messages.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <EmptyState message="No messages yet. Run a workflow to see messages here." />
                </td>
              </tr>
            ) : (
              messages.map(msg => (
                <tr key={msg.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800 capitalize">
                      {msg.channel}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {msg.from_agent_id ? msg.from_agent_id.slice(0, 8) : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {msg.to_agent_id ? msg.to_agent_id.slice(0, 8) : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm max-w-md whitespace-pre-wrap break-words">{msg.content}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(msg.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
