# Unofficial Claude API For Python

The UNOFFICIAL free API for Anthropic's Claude LLM.

## Background

Claude is [Anthropic's](https://www.anthropic.com/) LLM app (similar to ChatGPT). This library allows you to use the API (for free) and interact with it in your python projects.

## Implemented actions:
The Unofficial Claude API is under active development. The following endpoints are usable in some capacity:

- Getting organizations you're in
- Getting conversations you're in
- Starting a conversation
- Sending a message and receiving a response
- Delete a conversation
- Create an attachment from a file
- Send attachments
- getting message history

Note that the api is __**synchronous**__.

## TODO features
- Tests
- Fixing models OTHER than `claude_2`
- asynchronous mode
- Better caching
- cleaner errors and passing these up to users


This project is under active development and is extremely unstable, so there are no guarantees it will work for you. If you find a bug or you think it should work in a scenario where it doesn't, file an issue.


## Usage

### Step 1
Install the library using the following:
```
pip install claude-api-py
```

If that doesn't work, you can install directly from this github repository:

```
pip install git+git://github.com/AshwinPathi/claude-api-py.git
```

There is one requirement as of now:
- `sseclient-py` [link here](https://github.com/mpetazzoni/sseclient)


### Step 2
Get a `sessionKey` from the Claude website. You will need this to start the bot. Ideally also have a user agent of the computer you use to access claude.

You can get this information by logging into `https://claude.ai/chats` and doing the following:

1. open inspect element (f12 on chrome)
2. On the top bar, go to the `Application` tab.
3. Under `Storage`, go to `Cookies`.
4. look for a cookie called `https://claude.ai`, click it.
5. click the `sessionKey` field, and copy the session key down. It should begin with `sk-ant-sid01...`


### Step 3
Use the bot. You can see an example at `example.py`.

### Examples:

#### Importing the necessary libraries
```py
# The ClaudeClient is the raw API that gives you access to all organization and conversation level API calls
# with a simple python interface. However, you have to pass organization_uuid and conversation_uuid everywhere, so
# its not ideal if you want a simple to use API.
from claude import claude_client

# The ClaudeWrapper takes in a claude client instance and allows you to use a single organization and conversation
# context. This allows you to use the API more ergonomically.
from claude import claude_wrapper
```

#### Create the client and wrapper
```py
client = claude_client.ClaudeClient(SESSION_KEY)

organizations = client.get_organizations()
# You can omit passing in the organization uuid and the wrapper will assume
# you will use the first organization instead.
claude_obj = claude_wrapper.ClaudeWrapper(client, organization_uuid=organizations[0]['uuid'])
```

#### Starting a new conversation
```py
conversation_uuid = claude_obj.start_new_conversation("New Conversation", "Hi Claude!")
```

#### Send a message (passing in the client uuid)
```py
conversation_uuid = claude_obj.get_conversations()[0]['uuid']
response = claude_obj.send_message("How are you doing today!", conversation_uuid=conversation_uuid)
```

#### Setting a conversation context and sending a message
```py
conversation_uuid = claude_obj.get_conversations()[0]['uuid']
# This is so you don't have to constantly pass in conversation uuid on every call that requires it.
# anywhere that has an argument conversation_uuid=X can be omitted if you set the conversation context.
claude_obj.set_conversation_context(conversation_uuid)

response = claude_obj.send_message("How are you doing today!")
response = claude_obj.send_message("Who won the league of legends worlds 2022 finals?")
```

#### Sending an attachment
```py
# This generates an attachment in the right format
attachment = claude_obj.get_attachment('example_attachment.txt')
response = claude_obj.send_message("Hi Claude, what does this attachment say?", attachments=[attachment],
                                    conversation_uuid = conversation_uuid)
```

#### Deleting a conversation
```py
deleted = claude_obj.delete_conversation(conversation_uuid)
```

#### Deleting all conversations in an organization
```py
failed_deletions = claude_obj.delete_all_conversations()
assert len(failed_deletions) == 0
```

#### Renaming a conversation
```py
conversation = claude_obj.rename_conversation("New name", conversation_uuid = conversation_uuid)
```

#### Get conversation history
```py
conversation_history = claude_obj.get_conversation_info(conversation_uuid = conversation_uuid)
```


## Disclaimer
This library is for purely educational purposes and is UNOFFICIAL. I am not responsible if your account gets banned. If you would like to use the actual API, go to [anthropic website](https://docs.anthropic.com/claude/docs).
