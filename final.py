# Resources:
####***Notion MCP Project - Notion***####
# https://developers.notion.com/docs/get-started-with-mcp
# https://github.com/makenotion/notion-mcp-server?tab=readme-ov-file

##Example
# curl -X POST http://localhost:7001/run \
#   -H "Content-Type: application/json" \
#   -d '{"task": "Create a new page titled "Hello Notion MCP3" inside database with ID "2262c33bab9780c780e8fb0dab496ee0" with a text block "This is a test page created using MCP inside Autogen" in the Notion workspace.' "}'

####***ngrok***####
# #https://ngrok.com/
#https://ngrok.github.io/ngrok-python/

####***Flask***####
#https://github.com/pallets/flask/
#https://flask.palletsprojects.com/en/stable/

###***Autogen***####
#https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/components/workbench.html#mcp-workbench
#https://microsoft.github.io/autogen/stable//reference/python/autogen_ext.tools.mcp.html#autogen_ext.tools.mcp.StdioServerParams
#https://microsoft.github.io/autogen/stable//reference/python/autogen_ext.tools.mcp.html#autogen_ext.tools.mcp.mcp_server_tools
#https://microsoft.github.io/autogen/stable//reference/python/autogen_ext.models.openai.html#autogen_ext.models.openai.OpenAIChatCompletionClient
#https://microsoft.github.io/autogen/stable//reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.AssistantAgent
#https://microsoft.github.io/autogen/stable//reference/python/autogen_agentchat.teams.html#autogen_agentchat.teams.RoundRobinGroupChat
#https://microsoft.github.io/autogen/stable//reference/python/autogen_agentchat.conditions.html#autogen_agentchat.conditions.TextMentionTermination
#====================================================================================================

# Summary:
# This code sets up a Flask application that integrates with Notion MCP using Autogen.
# It allows users to run tasks that interact with their Notion workspace via a web interface.
# The application uses ngrok to expose the Flask server to the internet, enabling remote access.
# It also includes error handling and a health check endpoint to ensure the service is running.
# The main functionality is encapsulated in the `run_task` function, which processes tasks asynchronously.
# The Flask app listens for POST requests on the `/run` endpoint, where users can submit tasks to be executed by the Notion MCP agent.
# The application is designed to be run locally, with ngrok providing a public URL for external access.

## Import necessary libraries
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
import os
from flask import Flask,jsonify,request
from pyngrok import ngrok
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve Notion and OpenAI API keys from environment variables
NOTION_API_KEY = os.environ['NOTION_SECRET']
OPENAI_API_KEY=os.environ['OPENAI_API_KEY']
NGROK_AUTH_TOKEN= os.environ['NGROK_AUTH_TOKEN']


# Set the port for Flask and ngrok
port = 7001

# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app)

# Define the system message for the Notion MCP agent
SYSTEM_MESSAGE = "You are a helpful assistant that can search and summarize content from the user's Notion workspace and also list what is asked.Try to assume the tool and call the same and get the answer. Say TERMINATE when you are done with the task."

# Function to configure the Notion MCP agent and team
async def setup_team():
    
    # Set up the MCP server parameters
    # Use npx.cmd for Windows compatibility, or npx for other systems
    # Uncomment the command line based on your OS
    # command="npx.cmd"  # Use this line if you're on Windows
    # command="npx"  # Uncomment this line if you're not on Windows  
    params = StdioServerParams(
        command="npx.cmd",  # Use npx.cmd for Windows compatibility
        # command="npx",  # Uncomment this line if you're not on Windows
        args=['-y','mcp-remote','https://mcp.notion.com/mcp'],
        env={
            'NOTION_API_KEY':NOTION_API_KEY
        },
        read_timeout_seconds=20
    )
    
    # Initialize the OpenAI model client
    # Use gpt-4o-mini model for the agent
    # You can change the model as per your requirement
    model = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=OPENAI_API_KEY
    )
    # Get the MCP tools using the server parameters
    # This will allow the agent to interact with Notion MCP
    # The mcp_server_tools function sets up the necessary tools for the agent
    mcp_tools= await mcp_server_tools(server_params=params)
    
    # Create the Notion MCP agent
    # The agent will use the system message, model client, and MCP tools
    # reflect_on_tool_use=False means the agent won't reflect on its tool usage
    # You can set it to True if you want the agent to reflect on its actions
    # This can be useful for debugging or improving the agent's performance
    agent= AssistantAgent(
        name='notion_agent',
        system_message=SYSTEM_MESSAGE,
        model_client=model,
        tools=mcp_tools,
        reflect_on_tool_use=False
    )
    
    # Create a team for the agent using RoundRobinGroupChat
    # This allows the agent to participate in a group chat with round-robin scheduling
    # max_turns=5 means the team will have a maximum of 5 turns before terminating
    # termination_condition=TextMentionTermination('TERMINATE') means the team will terminate when 'TERMINATE' is mentioned
    team = RoundRobinGroupChat(
        participants=[agent],
        max_turns=5,
        termination_condition=TextMentionTermination('TERMINATE')
    )

    return team

# Function to orchestrate the team and run the task
async def run_task(task:str)->str:
    # Set up the team using the setup_team function
    # This will configure the Notion MCP agent and its tools
    # The team will be used to run the task asynchronously
    team = await setup_team()
    output = []
    async for msg in team.run_stream(task=task):
        output.append(str(msg))

    # Basic success check — you can improve this with richer parsing if needed
    success_message = ""
    joined_output = "\n\n\n".join(output)
    if "error" not in joined_output.lower():
        success_message = "\n\n✅ Task completed successfully."
    else:
        success_message = "\n\n⚠️ Task completed with errors."

    return joined_output + success_message

# Set up ngrok with the authentication token
# Flask routes

@app.route('/health',methods=['GET'])
def health():
    return jsonify({"status":'ok','message':'Notion MCP Flask App is live'}),200

# Route to check if the app is running
@app.route('/',methods=['GET'])
def root():
    return jsonify({'message':' MCP Notion app is live, use /health or /run to work '}),200

# Route to run the task
# This endpoint accepts a POST request with a task in JSON format
# The task should be a string describing the action to be performed in Notion MCP
# The run_task function will process the task and return the result
@app.route('/run',methods=['POST'])
def run():
    try:
        data = request.get_json()

        task = data.get('task')

        if not task:
            return jsonify ({'error':'Missing Task'}), 400
        
        print(f'Got the task {task}')

        result = asyncio.run(run_task(task))

        return jsonify({'status':'sucess','result':result}),200
        
    except Exception as e:
        return jsonify({'status':'error','result':str(e)}),500


# Main function to run the Flask app and ngrok
# This function sets up ngrok and starts the Flask app
# It also prints the public URL for accessing the app
# You can run this script to start the server and expose it via ngrok
if __name__=='__main__':
    
    # Set up ngrok with the authentication token
    # This will allow ngrok to create a secure tunnel to the Flask app
    # Make sure to replace NGROK_AUTH_TOKEN with your actual ngrok auth token
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    public_url = ngrok.connect(port)
    print(f"Public URL:{public_url}/api/hello \n \n")
    
    # Start the Flask app
    # The app will listen on the specified port (7001)
    app.run(port = port)
    
#===================
# Goto Lovable
#===================
# After running the script, you can access the app at the public URL provided by ngrok.
# You can use tools like Postman or curl to send POST requests to the /run endpoint with your tasks.
# Example task:
# {
#   "task": "Create a new page titled 'Hello Notion MCP' inside database with ID '2262c33bab9780c780e8fb0dab496ee0' with a text block 'This is a test page created using MCP inside Autogen' in the Notion workspace."
# }
# This will create a new page in your Notion workspace using the MCP agent.
# Create Front end using Lovable or any other framework to interact with this Flask app.
# https://lovable.dev/
# Prompt for Lovable:
# "Create a web interface that allows users to input tasks for the Notion MCP agent. The interface should have a text input 
# for the task and a submit button. When the user submits a task, it should send a POST request to the /run endpoint of the Flask app with the task in JSON format. Display the result of the task in a user-friendly manner."
# You can also use the /health endpoint to check if the app is running.
# The app is designed to handle tasks related to Notion MCP, such as creating pages, updating content, and more.
# ngrok url: https://07170a524529.ngrok-free.app/health
# Example curl command to test the /run endpoint:
# curl -X POST http://localhost:7001/run \
#   -H "Content-Type: application/json" \
#   -d '{"task": "Create a new page titled "Hello Notion MCP" inside database with ID "2262c33bab9780c780e8fb0dab496ee0" with a text block "This is a test page created using MCP inside Autogen" in the Notion workspace.' "}'
# Available endpoints:
# /health
# /
# /run (I have given you the curl for this which I could be able to edit.)
#===================
