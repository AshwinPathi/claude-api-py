import src.constants as constants
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import src.custom_requests as requests
from src.custom_requests import JsonType, HeaderType


class RequestType(Enum):
    """Simple enum to determine what type of request to send."""

    GET = 0
    POST = 1
    DELETE = 2


@dataclass(frozen=True)
class OrganizationContext:
    """Data about the users' organization, which determines what actions they can take
    and what chats they have open.
    """

    uuid: str
    name: str
    join_token: str
    capabilities: List[str]


@dataclass(frozen=True)
class ConversationContext:
    """Data about a users' conversations."""

    uuid: str
    name: str
    summary: str
    organization: OrganizationContext


class ClaudeAPI:
    def __init__(
        self,
        session_key: str,
        base_url: str = constants.BASE_URL,
        spoofed_headers: Optional[HeaderType] = None,
    ):
        """Setup the claude API With a session_key.

        You can access the session key by going to the claude.ai chat app, going
        to the `inspect element` view, going to `Application` settings, going to
        `cookies --> claude.ai` and using the `sessionKey` cookie.
        """
        self._session_key = session_key
        self._base_url = base_url
        if spoofed_headers is not None:
            self._spoofed_headers = spoofed_headers
        else:
            self._spoofed_headers = {}

        self._validate_params()

        self._clear_conversation_context()

    ####################################################################
    #                                                                  #
    #                         Public APIs                              #
    #                                                                  #
    ####################################################################

    def send_message(
        self,
        message: str,
        conversation: Optional[ConversationContext] = None,
        timezone: constants.Timezone = constants.Timezone.LA,
        model: constants.Model = constants.Model.CLAUDE_2,
    ) -> str:
        """Sends a |message| to claude on the inputted (or current) |conversation|. Can optionally
        provide a timezone and model.
        """
        conversation = self._get_conversation_context(conversation)
        if conversation is None:
            raise RuntimeError("No conversation context provided or set.")
        return self._send_message(
            conversation.organization.uuid, conversation.uuid, message, timezone, model
        )

    def start_conversation(
        self, organization: OrganizationContext, message: str, conversation_name: str
    ) -> Optional[ConversationContext]:
        """Start a new conversation with claude in |organization|, sending an initial |message|"""
        return self._create_conversation(organization.uuid, message, conversation_name)

    def get_conversation_info(
        self, conversation: Optional[ConversationContext] = None
    ) -> JsonType:
        """Get full conversation info for the given conversation (or current conversation context)"""
        conversation = self._get_conversation_context(conversation)
        if conversation is None:
            raise RuntimeError("No conversation context provided or set.")
        return self._get_conversation_info(
            conversation.organization.uuid, conversation.uuid
        )

    def clear_conversations(
        self, organization: OrganizationContext
    ) -> List[ConversationContext]:
        conversations = self._get_conversations_from_org(organization.uuid)
        failed = []
        for conversation in conversations:
            if self._delete_conversation_from_org(
                conversation.organization.uuid, conversation.uuid
            ):
                failed.append(conversation)
        return failed

    def delete_conversation(
        self, conversation: Optional[ConversationContext] = None
    ) -> bool:
        conversation = self._get_conversation_context(conversation)
        if conversation is None:
            raise RuntimeError("No conversation context provided or set.")
        return self._delete_conversation_from_org(
            conversation.organization.uuid, conversation.uuid
        )

    def get_conversations(
        self, organization: OrganizationContext
    ) -> List[ConversationContext]:
        return self._get_conversations_from_org(organization.uuid)

    def get_organizations(self) -> List[OrganizationContext]:
        """Gets a list of the organizations that the user is in."""
        return self._get_organization_data()

    def switch_conversation_context(
        self, conversation_context: ConversationContext
    ) -> None:
        """Switches current conversation context to |conversation_context|"""
        self._switch_conversation_context(conversation_context)

    def clear_conversation_context(self) -> None:
        """Clears the current conversation context."""
        self._clear_conversation_context()

    ####################################################################
    #                                                                  #
    #                       Helper Methods                             #
    #                                                                  #
    ####################################################################

    def _send_message(
        self,
        organization_uuid: str,
        conversation_uuid: str,
        message: str,
        timezone: constants.Timezone,
        model: constants.Model,
    ) -> str:
        """Sends a |message| to the given |organization_uuid| and |conversation_uuid|.
        Note: uses streamed requests.
        """

        request_body = {
            "organization_uuid": organization_uuid,
            "conversation_uuid": conversation_uuid,
            "text": message,
            "attachments": [],  # TODO Attachments aren't supported at the moment. They have to use some complex encoding scheme.
            "completion": {"prompt": message, "timezone": timezone, "model": model},
        }

        default_headers = self._get_request_header()
        header = self._attach_necessary_headers(default_headers)
        header["accept"] = "text/event-stream,text/event-stream"
        last_message = ""
        for streamed_response in requests.sse(
            constants.BASE_URL + constants.APPEND_MESSAGE_API_ENDPOINT,
            headers=header,
            request_body=request_body,
        ):
            last_message = streamed_response

        if not last_message:
            return last_message
        return json.loads(last_message)["completion"]

    def _create_conversation(
        self, organization_uuid: str, initial_message: str, conversation_name: str
    ) -> Optional[ConversationContext]:
        """Creates a new conversation with the name |conversation_name|. Returns a new conversation
        context if successful, otherwise returns None. Also creates a title for the new conversation.
        """
        conversation_uuid = str(uuid.uuid4())
        response = self._request_internal(
            constants.START_CONVERSATION_API_ENDPOINT.format(
                organization_uuid=organization_uuid
            ),
            request_type=RequestType.POST,
            request_body={"name": "", "uuid": conversation_uuid},
        )
        if response.ok:
            _ = self._send_message(
                organization_uuid,
                conversation_uuid,
                initial_message,
                timezone=constants.Timezone.LA,
                model=constants.Model.CLAUDE_2,
            )
            if self._generate_chat_title(
                organization_uuid, conversation_uuid, initial_message
            ):
                organization = self._get_organization_context_by_uuid(organization_uuid)
                if organization is None:
                    return None
                return ConversationContext(
                    uuid=conversation_uuid,
                    name=conversation_name,
                    summary="",
                    organization=organization,
                )
        return None

    def _generate_chat_title(
        self, organization_uuid: str, conversation_uuid: str, message: str
    ) -> bool:
        """Generates a title for a chat."""
        recent_conversations = self._get_conversations_from_org(organization_uuid)
        response = self._request_internal(
            constants.GENERATE_CHAT_TITLE_API_ENDPOINT,
            request_type=RequestType.POST,
            request_body={
                "organization_uuid": organization_uuid,
                "conversation_uuid": conversation_uuid,
                "message_content": message,
                "recent_titles": [convo.name for convo in recent_conversations],
            },
        )
        return response.ok

    def _get_conversation_info(
        self, organization_uuid: str, conversation_uuid: str
    ) -> JsonType:
        """Return the conversation info in JSON format from a given conversation."""
        response = self._request_internal(
            constants.GET_CONVERSATION_INFO_API_ENDPOINT.format(
                organization_uuid=organization_uuid, conversation_uuid=conversation_uuid
            ),
            request_type=RequestType.GET,
        )
        if not response.ok:
            return {}

        return response.json()

    def _get_conversations_from_org(
        self, organization_uuid: str
    ) -> List[ConversationContext]:
        """Gets metadata about a users conversations in a particular organization."""
        response = self._request_internal(
            constants.GET_CONVERSATIONS_API_ENDPOINT.format(
                organization_uuid=organization_uuid
            ),
            request_type=RequestType.GET,
        )
        if not response.ok:
            return []

        response_json = response.json()

        organization_context = self._get_organization_context_by_uuid(organization_uuid)
        if organization_context is None:
            return []

        conversations = []

        for conversation in response_json:
            conversations.append(
                ConversationContext(
                    uuid=conversation["uuid"],
                    name=conversation["name"],
                    summary=conversation["summary"],
                    organization=organization_context,
                )
            )

        return conversations

    def _delete_conversation_from_org(
        self, organization_uuid: str, conversation_uuid: str
    ) -> bool:
        """Removes a conversation |conversation_uuid| from the organization |organization_uuid|."""
        response = self._request_internal(
            constants.DELETE_CONVERSATION_API_ENDPOINT.format(
                organization_uuid=organization_uuid, conversation_uuid=conversation_uuid
            ),
            request_type=RequestType.DELETE,
            custom_header={"cookie": f"sessionKey={self._session_key}"},
        )
        return response.ok

    def _get_organization_context_by_uuid(
        self, target_organization_uuid: str
    ) -> Optional[OrganizationContext]:
        """Get an organization context by its uuid."""
        organization_data = self._get_organization_data()
        for organization in organization_data:
            if organization.uuid == target_organization_uuid:
                return organization
        return None

    def _get_organization_data(self) -> List[OrganizationContext]:
        """Get metadata about the users' organizations."""
        response = self._request_internal(
            constants.GET_ORGANIZATIONS_API_ENDPOINT, request_type=RequestType.GET
        )
        if not response.ok:
            return []

        response_json = response.json()

        organizations = []

        for organization in response_json:
            organizations.append(
                OrganizationContext(
                    uuid=organization["uuid"],
                    name=organization["name"],
                    join_token=organization["join_token"],
                    capabilities=organization["capabilities"],
                )
            )

        return organizations

    def _request_internal(
        self,
        api_endpoint: str,
        request_type: RequestType,
        request_body: Optional[JsonType] = None,
        custom_header: Optional[HeaderType] = None,
    ) -> requests.Response:
        """Internal request method that wraps requests to the claude API with
        the correct headers, proxy, and retry parameters.
        """
        response = None

        # Always add spoofed headers to the internal request, unless its overrwritten by the
        # incoming |custom_header|.
        default_headers = custom_header or self._get_request_header()
        header = self._attach_necessary_headers(default_headers)
        full_url = self._base_url + api_endpoint

        if request_type == RequestType.GET:
            response = requests.get(full_url, headers=header)
        elif request_type == RequestType.POST:
            response = requests.post(
                full_url, headers=header, request_body=request_body
            )
        elif request_type == RequestType.DELETE:
            response = requests.delete(full_url, headers=header)
        else:
            raise RuntimeError("Invalid Request Type")

        return response

    def _get_request_header(self) -> Dict[str, str]:
        """Returns the default header that all requests have to contain. Has information about
        the secret key thats used to interact with anthropic APIs.
        """
        return {
            "content-type": "application/json",
            "cookie": f"sessionKey={self._session_key}",
        }

    def _attach_necessary_headers(
        self, input_headers: Optional[HeaderType]
    ) -> HeaderType:
        if input_headers is None:
            return self._spoofed_headers
        modifyable_headers = input_headers.copy()
        # Inject custom header values into the input headers, as long
        # as the input headers has not modified any specific value.
        for header_key, header_value in self._spoofed_headers.items():
            if header_key not in input_headers:
                modifyable_headers[header_key] = header_value
        return modifyable_headers

    def _validate_params(self):
        """Performs some assertions to make sure that input parameters are correct."""
        assert self._session_key, "Session key is None or non-existent."
        assert self._session_key.startswith('sk-ant-sid01-'), "Session key is malformed."
        assert self._base_url == constants.BASE_URL, "Base URL is invalid."

    def _get_conversation_context(
        self, conversation_context_fallback: Optional[ConversationContext] = None
    ) -> Optional[ConversationContext]:
        """Gets the current conversation context with a fallback context."""
        if conversation_context_fallback is not None:
            return conversation_context_fallback
        if self._current_conversation_context is not None:
            return self._current_conversation_context
        return None

    def _switch_conversation_context(
        self, conversation_context: ConversationContext
    ) -> None:
        """Switches the current conversation to |conversation_context|"""
        self._current_conversation_context = conversation_context

    def _clear_conversation_context(self) -> None:
        """Clears the current conversation."""
        self._current_conversation_context = None
