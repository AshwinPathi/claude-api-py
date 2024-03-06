"""Example showcasing how to use the Unofficial Claude API"""
import os
import pprint
import time

from dotenv import load_dotenv


# The ClaudeClient is the raw API that gives you access to all organization and conversation level API calls
# with a simple python interface. However, you have to pass organization_uuid and conversation_uuid everywhere, so
# its not ideal if you want a simple to use API.
from claude import claude_client, constants

# The ClaudeWrapper takes in a claude client instance and allows you to use a single organization and conversation
# context. This allows you to use the API more ergonomically.
from claude import claude_wrapper

# session key is stored in .env file for the sake of example.
load_dotenv()
SESSION_KEY = str(os.environ.get("SESSION_KEY"))


# Note that there are intentional 1 second delays between API calls to ensure that you don't
# get rate limited.
def main():
    client = claude_client.ClaudeClient(SESSION_KEY)
    organizations = client.get_organizations()

    # Wraps the client api and organization into a single organization.
    claude_obj = claude_wrapper.ClaudeWrapper(client, organizations[0]['uuid']) # type: ignore

    # We can list our existing conversations here.
    conversations = claude_obj.get_conversations()
    original_num_convos = len(conversations) # type: ignore
    print("Listing current conversations:")
    pprint.pprint(conversations)
    print()
    time.sleep(1)

    model = constants.Model.CLAUDE_OPUS
    
    # First, lets create a new chat.
    new_convo_response = claude_obj.start_new_conversation("New Conversation", "Hi Claude!", model=model)
    assert new_convo_response is not None
    print("Title of new chat: ", new_convo_response['title'])
    # You can get the initial response with:
    # initial_response = new_convo_response['response']
    conversation_uuid = new_convo_response['uuid']

    # Listing the conversations again we can see that we have a new conversation
    conversations = claude_obj.get_conversations()
    assert len(conversations) == original_num_convos + 1 # type: ignore
    print("Listing conversations after we made a new one")
    pprint.pprint(conversations)
    print()
    time.sleep(1)


    # send a message without the context set:
    response = claude_obj.send_message("How are you doing today!", conversation_uuid=conversation_uuid, model=model)
    print("Printing out the response of sending a message")
    pprint.pprint(response)
    print()
    time.sleep(1)
    """Response here would look something like:

        {'completion': ' Hi there! Nice to meet you.',
        'log_id': '...',
        'messageLimit': {'type': 'within_limit'},
        'model': 'claude-2.0',
        'stop': '\n\nHuman:',
        'stop_reason': 'stop_sequence'}
    
    The actual result will be in the `completion` field.
    """

    # set the context and send a message, so subsequent messages don't need to pass in the
    # conversation uuid.
    claude_obj.set_conversation_context(conversation_uuid)
    response = claude_obj.send_message("How are you doing today?", model=model)
    print("Send another message")
    pprint.pprint(response)
    print()
    time.sleep(1)


    # Send an attachment to claude and ask it to output some information about it.
    # First generate the attachment.
    attachment = claude_obj.get_attachment('example_attachment.txt')
    if attachment is None:
        print("Getting attachment failed.")
        return
    response = claude_obj.send_message("Hi Claude, what does this attachment say?", attachments=[attachment], model=model)
    print("Checking attachment response")
    pprint.pprint(response)
    print()
    time.sleep(1)


    # Finally, delete the conversation we just made.
    deleted = claude_obj.delete_conversation(conversation_uuid)
    assert deleted

    # Check to see that we have the same number of conversations as before.
    conversations = claude_obj.get_conversations()
    assert len(conversations) == original_num_convos # type: ignore
    print("List the active conversations we have again, it should be the same as the first one.")
    pprint.pprint(conversations)
    print()
    time.sleep(1)



if __name__ == '__main__':
    main()
