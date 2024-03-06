"""Global constants for the claude api."""
from enum import Enum

####################################################################
#                                                                  #
#                         API constants                            #
#                                                                  #
####################################################################

# Base url for all claude API requests.
BASE_URL = "https://claude.ai"

# API endpoint for getting user organization information.
GET_ORGANIZATIONS_API_ENDPOINT = "/api/organizations"

# API endpoint for getting user chat information. Note that this has
# to be prefixed with the UUID of an organization that the user is in.
GET_CONVERSATIONS_API_ENDPOINT = (
    GET_ORGANIZATIONS_API_ENDPOINT + "/{organization_uuid}/chat_conversations"
)

# API endpoint to start a conversation.
START_CONVERSATION_API_ENDPOINT = GET_CONVERSATIONS_API_ENDPOINT

# API endpoint for generating a chat title.
GENERATE_CHAT_TITLE_API_ENDPOINT = "/api/generate_chat_title"

# API endpoint to send a message
APPEND_MESSAGE_API_ENDPOINT = "/api/append_message"

# API endpoint to delete a conversation.
DELETE_CONVERSATION_API_ENDPOINT = (
    GET_CONVERSATIONS_API_ENDPOINT + "/{conversation_uuid}"
)

# API endpoint to get conversation info.
GET_CONVERSATION_INFO_API_ENDPOINT = (
    GET_CONVERSATIONS_API_ENDPOINT + "/{conversation_uuid}"
)

# API endpoint to rename a conversation
RENAME_CONVERSATION_API_ENDPOINT = "/api/rename_chat"

# API endpoint to upload a file and convert it to an attachment.
CONVERT_DOCUMENT_API_ENDPOINT = "/api/convert_document"

# Common headers that are used to bypass 403s.
# Note that this doesn't contain user agent.
HEADERS = {
    "content-type": "application/json",
    "authority": "claude.ai",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "dnt": "1",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "upgrade-insecure-requests": "1",
    "connection": "keep-alive",
}

# User agent you can use by default. Its reccomended to change this to the user agent your browser uses
# when you log into anthropic. This is just here as a default.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
)

####################################################################
#                                                                  #
#                 Message sending constants                        #
#                                                                  #
####################################################################


###### Timezones
class Timezone(str, Enum):
    NYC = "America/New_York"
    LA = "America/Los_Angeles"

    def __str__(self) -> str:
        return self.value


###### Models
class Model(str, Enum):
    CLAUDE_2_P_0 = "claude-2.0"
    CLAUDE_2_P_1 = "claude-2.1"
    CLAUSE_INSTANT_1_P_2 = "claude-instant-1.2"
    CLAUDE_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_OPUS = "claude-3-opus-20240229"

    def __str__(self) -> str:
        return self.value
