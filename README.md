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
api.send_message(conversation[0], 'Hi Claude!')
```
