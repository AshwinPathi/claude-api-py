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
    CLAUDE_2 = "claude-2"
    CLAUDE_1_P_3 = "claude-1.3"
    CLAUDE_INSTANT_100k = "claude-instant-100k"

    def __str__(self) -> str:
        return self.value
