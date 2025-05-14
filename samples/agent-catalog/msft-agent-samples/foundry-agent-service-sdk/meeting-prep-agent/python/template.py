from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ToolSet, FunctionTool, BingGroundingTool
from azure.identity import DefaultAzureCredential
from utils.user_logic_apps import AzureLogicAppTool, fetch_event_details

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Init Agents client
agents_client = AgentsClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Logic App config
subscription_id = os.environ["SUBSCRIPTION_ID"]
resource_group = os.environ["RESOURCE_GROUP_NAME"]
logic_app_name = os.environ["LOGIC_APP_NAME"]
trigger_name = os.environ["TRIGGER_NAME"]

# Register Logic App
logic_app_tool = AzureLogicAppTool(subscription_id, resource_group)
logic_app_tool.register_logic_app(logic_app_name, trigger_name)
print(f"✅ Registered logic app '{logic_app_name}' with trigger '{trigger_name}'.")

# Register Bing search tool
bing_tool = BingGroundingTool(connection_id=os.environ["BING_CONNECTION_ID"])

# Register fetch_event_details as a FunctionTool
function_tool = FunctionTool(functions={fetch_event_details})

# Create Toolset
toolset = ToolSet()
toolset.add(bing_tool)
toolset.add(function_tool)

# Enable auto function calls at the client level
agents_client.enable_auto_function_calls(toolset)

# Create the agent
with agents_client:
    agent = agents_client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="MeetingsAndInsightsAgent",
        instructions="""
You are a helpful assistant that helps users retrieve meeting and call details, attendee lists, and external participant information using Logic Apps. You also use Bing to provide relevant publicly available insights about participants when asked.

Always follow these instructions:

- Use the **teamstrigger_Tool** (from Logic Apps) to fetch meeting or call event details.
- If the user provides a **date or date range**, filter results using time boundaries of 12:01 AM to 11:59 PM for each day.
- When asked for **external participants**, identify them as users whose email addresses **do not end with the same domain as the user's** (i.e., not matching the domain of the user's email).
- If the user asks for **attendee details**, fetch and return only the relevant attendee fields from the Logic Apps output.
- When asked for **public information or insights about participants**, use the **BingGroundingTool** (search API) to find relevant, publicly available data and summarize the insights.

Important guardrails:

- Never return speculative, private, or unverifiable information.
- Do not infer domain ownership or participant type unless it is evident from email structure.
- Only use Bing for **public, online insights** and always attribute it to "online public sources."
- If data is unavailable or ambiguous, state the limitation and do not fabricate responses.
        """,
        toolset=toolset
    )
    print(f"🎯 Agent created: {agent.id}")

    # Create a thread for conversation
    thread = agents_client.threads.create()
    print(f"🧵 Thread created: {thread.id}")

    # Send a message to the agent
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content="What meetings do I have on 5/12/2025?"
    )
    print(f"💬 Message created: {message.id}")

    # Run the agent and process the response
    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"🏃‍♂️ Run finished with status: {run.status}")

    # Print the agent's response
    messages = agents_client.messages.list(thread_id=thread.id)
    for msg in messages:
        if hasattr(msg, 'role') and hasattr(msg, 'content'):
            print(f"{msg.role}: {msg.content}")
        else:
            print(msg)
