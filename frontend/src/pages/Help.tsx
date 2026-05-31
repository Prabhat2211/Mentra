export default function Help() {
  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-bold mb-6">Help & Examples</h2>

      {/* Adding a New Agent */}
      <section className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold mb-3">Adding a New Agent</h3>
        <p className="text-sm text-gray-600 mb-4">
          Agents are the building blocks of your workflows. Each agent has a role, personality, tools, and LLM configuration.
        </p>

        <div className="mb-4">
          <h4 className="font-medium text-sm mb-2">Example: Create a "Research Analyst" Agent</h4>
          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
            <li>Go to <strong>Agents</strong> and click <strong>+ Create Agent</strong></li>
            <li>Set <strong>Name</strong> to <code className="bg-gray-100 px-1 rounded">Research Analyst</code></li>
            <li>Set <strong>Role</strong> to <code className="bg-gray-100 px-1 rounded">Deep research specialist</code></li>
            <li>Set <strong>System Prompt</strong> to something like:
              <pre className="bg-gray-50 p-3 rounded-lg text-xs mt-1 overflow-x-auto">
{`You are a research analyst. Given a topic, produce structured findings covering:
- Key facts and statistics
- Current trends and developments
- Expert opinions and consensus
- Risks and opportunities

Be thorough and cite specific data points where possible.`}
              </pre>
            </li>
            <li>Choose a <strong>Personality</strong> (e.g., Professional)</li>
            <li>Select <strong>Tools</strong> like <code className="bg-gray-100 px-1 rounded">web_search_stub</code> and <code className="bg-gray-100 px-1 rounded">save_note</code></li>
            <li>Click <strong>Create Agent</strong></li>
          </ol>
        </div>

        <div className="border-t pt-4">
          <h4 className="font-medium text-sm mb-2">Tips</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
            <li>Give agents specific roles — the system prompt determines their behavior in a workflow</li>
            <li>Use <strong>Personality</strong> to control tone: polite for customer-facing, casual for internal tools</li>
            <li>Enable <strong>Memory</strong> if the agent needs conversation history across chained steps</li>
            <li><strong>Guardrails</strong> are injected into the prompt after the system prompt — use them for safety rules like "never reveal the API key"</li>
            <li>Toggle <strong>LLM Configuration</strong> to override the global provider per-agent (e.g., one agent uses Groq, another uses Gemini)</li>
          </ul>
        </div>
      </section>

      {/* Adding a New Workflow Template */}
      <section className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold mb-3">Adding a New Workflow Template</h3>
        <p className="text-sm text-gray-600 mb-4">
          Workflow templates define multi-agent execution flows. Create one when you need a reusable pattern that can be assigned different agents.
        </p>

        <ol className="list-decimal list-inside space-y-3 text-sm text-gray-700 mb-4">
          <li>
            <strong>Create the template file</strong> under <code className="bg-gray-100 px-1 rounded">app/templates/my_template.py</code>
          </li>
          <li>
            <strong>Define the template</strong> using the <code className="bg-gray-100 px-1 rounded">WorkflowTemplate</code> dataclass:
            <pre className="bg-gray-50 p-3 rounded-lg text-xs mt-2 overflow-x-auto">
{`from app.templates.types import WorkflowTemplate

MY_TEMPLATE = WorkflowTemplate(
    key="my_template",
    name="My Custom Flow",
    description="Describe what this workflow does.",
    nodes=["agent_a", "agent_b"],
    edges=[("human", "agent_a"), ("agent_a", "agent_b"), ("agent_b", "human")],
    sample_input="What does this workflow process?",
    default_config={
        "roles": {
            "agent_a": "First agent's role description.",
            "agent_b": "Second agent's role description.",
        },
        "tools": ["web_search_stub", "save_note"],
    },
)`}
            </pre>
          </li>
          <li>
            <strong>Register it</strong> in <code className="bg-gray-100 px-1 rounded">app/templates/registry.py</code>:
            <pre className="bg-gray-50 p-3 rounded-lg text-xs mt-2 overflow-x-auto">
{`from app.templates.my_template import MY_TEMPLATE

TEMPLATES = {
    RESEARCH_SUMMARY_TEMPLATE.key: RESEARCH_SUMMARY_TEMPLATE,
    FINANCIAL_ASSISTANT_TEMPLATE.key: FINANCIAL_ASSISTANT_TEMPLATE,
    MY_TEMPLATE.key: MY_TEMPLATE,  # ← add this line
}`}
            </pre>
          </li>
          <li>
            <strong>Add handler functions</strong> (optional) in <code className="bg-gray-100 px-1 rounded">app/runtime/graph.py</code> if your template needs custom logic beyond the generic agent execution:
            <pre className="bg-gray-50 p-3 rounded-lg text-xs mt-2 overflow-x-auto">
{`def _my_agent_a(state: WorkflowState, db: Database) -> WorkflowState:
    # Custom logic here
    state.output = f"Processed: {state.user_input}"
    return state`}
            </pre>
          </li>
          <li>
            <strong>Add the template to the frontend</strong> in <code className="bg-gray-100 px-1 rounded">frontend/src/pages/WorkflowCreate.tsx</code> — add a new entry to the <code className="bg-gray-100 px-1 rounded">TEMPLATES</code> array with the key, name, description, nodes, node labels, and node descriptions
          </li>
          <li>
            <strong>Add a test</strong> in <code className="bg-gray-100 px-1 rounded">tests/test_workflows.py</code> to verify execution
          </li>
        </ol>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
          <strong>Tip:</strong> After registering, the template appears in the UI at <strong>Workflows → Create Workflow</strong>. Users can assign their own agents to each node role.
        </div>
      </section>

      {/* Adding a New Messaging Channel */}
      <section className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold mb-3">Adding a New Messaging Channel</h3>
        <p className="text-sm text-gray-600 mb-4">
          Channels let external platforms (Telegram, Slack, WhatsApp) send messages to your workflows.
        </p>

        <ol className="list-decimal list-inside space-y-3 text-sm text-gray-700 mb-4">
          <li>
            <strong>Create the channel file</strong> under <code className="bg-gray-100 px-1 rounded">app/channels/slack.py</code>
          </li>
          <li>
            <strong>Implement the adapter</strong> — a polling or webhook-based receiver that:
            <pre className="bg-gray-50 p-3 rounded-lg text-xs mt-2 overflow-x-auto">
{`from app.db import Database
from app.runtime.graph import run_workflow
from app.config import settings

def handle_message(user_message: str, user_id: str) -> str:
    db = Database()
    db.init()
    
    # Find which workflow to run (or let user configure it)
    workflow_id = settings.default_slack_workflow_id
    if not workflow_id:
        workflows = db.list_workflows()
        if workflows:
            workflow_id = workflows[0]["id"]
    
    result = run_workflow(
        workflow_id=workflow_id,
        user_input=user_message,
        source_channel="slack",
        external_user_id=user_id,
        db=db,
    )
    return result.output`}
            </pre>
          </li>
          <li>
            <strong>Add config</strong> to <code className="bg-gray-100 px-1 rounded">app/config.py</code>:
            <pre className="bg-gray-50 p-3 rounded-lg text-xs mt-2 overflow-x-auto">
{`slack_bot_token: str | None = os.getenv("SLACK_BOT_TOKEN")
slack_enabled: bool = os.getenv("SLACK_ENABLED", "false").lower() == "true"
default_slack_workflow_id: str | None = os.getenv("DEFAULT_SLACK_WORKFLOW_ID")`}
            </pre>
          </li>
          <li>
            <strong>Add the entrypoint</strong> — a <code className="bg-gray-100 px-1 rounded">python -m app.channels.slack</code> command that starts polling or a webhook server
          </li>
          <li>
            <strong>Add env vars</strong> to <code className="bg-gray-100 px-1 rounded">.env.example</code> and your <code className="bg-gray-100 px-1 rounded">.env</code>
          </li>
          <li>
            <strong>Add a test</strong> in <code className="bg-gray-100 px-1 rounded">tests/test_channels.py</code>
          </li>
        </ol>

        <div className="border-t pt-4">
          <h4 className="font-medium text-sm mb-2">Reference Implementation</h4>
          <p className="text-sm text-gray-600">
            See <code className="bg-gray-100 px-1 rounded">app/channels/telegram.py</code> for a complete working example with:
          </p>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 mt-1">
            <li>Async message handling via <code className="bg-gray-100 px-1 rounded">python-telegram-bot</code></li>
            <li>Dynamic workflow switching with <code className="bg-gray-100 px-1 rounded">/use &lt;id&gt;</code></li>
            <li>Workflow listing with <code className="bg-gray-100 px-1 rounded">/workflows</code></li>
            <li>Non-blocking execution via <code className="bg-gray-100 px-1 rounded">run_in_executor</code></li>
          </ul>
        </div>
      </section>

      {/* Quick Reference */}
      <section className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Quick Reference</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 pr-4">Task</th>
              <th className="text-left py-2 pr-4">Where</th>
              <th className="text-left py-2">Key File</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            <tr>
              <td className="py-2 pr-4">Create an agent</td>
              <td className="py-2 pr-4">UI: Agents page</td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">/agents</code></td>
            </tr>
            <tr>
              <td className="py-2 pr-4">Add a template workflow</td>
              <td className="py-2 pr-4">Backend + Frontend</td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">app/templates/*.py</code></td>
            </tr>
            <tr>
              <td className="py-2 pr-4">Build a custom workflow</td>
              <td className="py-2 pr-4">UI: Builder page</td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">/builder</code></td>
            </tr>
            <tr>
              <td className="py-2 pr-4">Add a messaging channel</td>
              <td className="py-2 pr-4">Backend</td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">app/channels/*.py</code></td>
            </tr>
            <tr>
              <td className="py-2 pr-4">Schedule a workflow</td>
              <td className="py-2 pr-4">UI: Schedules page</td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">/schedules</code></td>
            </tr>
            <tr>
              <td className="py-2 pr-4">View logs & metrics</td>
              <td className="py-2 pr-4">UI: Monitoring / Dashboard</td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">/monitoring</code></td>
            </tr>
            <tr>
              <td className="py-2 pr-4">Set LLM provider</td>
              <td className="py-2 pr-4"><code className="bg-gray-100 px-1 rounded">.env</code></td>
              <td className="py-2"><code className="bg-gray-100 px-1 rounded">LLM_PROVIDER=groq|gemini|openai</code></td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  );
}
