# Unofficial (synchronous) Claude API For Python


## Disclaimer
This library is UNOFFICIAL and you might get banned for using it.

Its also under active development and is extremely unstable, so there are no guarantees it will work for you. If you find a bug or you think it should work in a scenario where it doesn't file an issue.


## Implemented actions:
- Getting organizations you're in
- Getting conversations you're in
- Starting a conversation
- Sending a message and receiving a response (can't send files yet)
- Delete a conversation


## Usage

### Step 1
Install the library using the following:
```
$pip install git+git://github.com/github.com/AshwinPathi/claude.git#egg=claude
```

### Step 2
Get a `sessionKey` from the Claude website. You will need this to start the bot.

### Step 1
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
