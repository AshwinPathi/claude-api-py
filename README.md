# Unofficial Claude API For Python

The UNOFFICIAL free API for Anthropic's Claude LLM.

## Implemented actions:
The Unofficial Claude API is under active development. The following endpoints are usable in some capacity:

- Getting organizations you're in
- Getting conversations you're in
- Starting a conversation
- Sending a message and receiving a response (can't send files yet)
- Delete a conversation
- Create an attachment from a file
- Send attachments

Note that the api is __**synchronous**__.


## Usage

### Step 1
Install the library using the following:
```
pip install git+git://github.com/github.com/AshwinPathi/claude.git#egg=claude
```

### Step 2
Get a `sessionKey` from the Claude website. You will need this to start the bot. Ideally also have a user agent of the computer you use to access claude.

### Step 3
Use the bot. You can see an example at `example.py`.


## Disclaimer
This library is UNOFFICIAL and you might get banned for using it. I am not responsible if your account gets banned. If you would like to use the actual API, go to the [anthropic website](https://docs.anthropic.com/claude/docs).

Its also under active development and is extremely unstable, so there are no guarantees it will work for you. If you find a bug or you think it should work in a scenario where it doesn't, file an issue.

