# Unofficial (synchronous) Claude API For Python

## Usage

### Step 1
Get a `sessionKey` from the Claude website. You will need this to start the bot.


### Step 2
Use the bot.
```py
from claude_impl import ClaudeAPI

session_key = ...

api = ClaudeAPI(session_key)

# Get a list of organizations you're in.
organizations = api.get_organizations()

# Get a list of conversations that you are in for the first organization.
conversations = api.get_conversations(organization[0])

# Send a message to the first conversation
response = api.send_message('Hi Claude!', conversation = conversation[0])

# Or, you can set the context and all subsequent calls will use that conversation.

api.switch_conversation_context(conversations[0])
response = api.send_message('Hi Claude!')
response = api.send_message('How are you doing today?')
```
