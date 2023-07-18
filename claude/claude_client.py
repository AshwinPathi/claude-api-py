"""Helper class to access Claude APIs via raw json."""
import json
from typing import List, Optional, Iterator, Union

from claude import constants
from claude import custom_requests
from claude.custom_types import JsonType, HeaderType


class ClaudeClient:
    """Acts as a lower level interface to the Claude API. Returns raw JSON
    structs and accepts lower level arguments to manipulate the Claude API.

    This can be used directly to interface with claude, but methods will require
    additional information to make calls. Its reccomended to use the wrapper
    implementations and pass in the client for the most flexibility.
    """

    def __init__(
        self,
        session_key: str,
        base_url: str = constants.BASE_URL,
        user_agent: str = constants.USER_AGENT,
        spoofed_headers: Optional[HeaderType] = None,
    ):
        self._session_key = session_key
        self._base_url = base_url
        self._user_agent = user_agent
        if spoofed_headers is None:
            self._spoofed_headers = constants.HEADERS
        else:
            self._spoofed_headers = spoofed_headers

    def send_message(
        self,
        organization_uuid: str,
        conversation_uuid: str,
        message: str,
        attachments: List,
        timezone: constants.Timezone,
        model: constants.Model,
        stream: bool = False,
    ) -> Union[Iterator[JsonType], Optional[JsonType]]:
        """Send a message to an organization/conversation. Stream mode will return a generator of the streamed responses,
        while unstreamed mode will return the last response that was received.
        """
        if stream:
            return self._send_message(
                organization_uuid,
                conversation_uuid,
                message,
                attachments,
                timezone,
                model,
            )
        else:
            return_val = None
            for elem in self._send_message(
                organization_uuid,
                conversation_uuid,
                message,
                attachments,
                timezone,
                model,
            ):
                return_val = elem
            return return_val

    def create_conversation(
        self, organization_uuid: str, new_conversation_uuid: str
    ) -> Optional[JsonType]:
        """Creates a conversation in the organization represented by |organization_uuid|,
        with a new conversation id of |new_conversation_uuid|.
        """
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.post(
            self._get_api_url(
                constants.START_CONVERSATION_API_ENDPOINT.format(
                    organization_uuid=organization_uuid
                )
            ),
            headers=header,
            request_body={"name": "", "uuid": new_conversation_uuid},
        )
        if not response.ok:
            return None
        return response.json()

    def delete_conversation(
        self, organization_uuid: str, conversation_uuid: str
    ) -> bool:
        """Removes a conversation |conversation_uuid| from the organization |organization_uuid|."""
        header = {}
        header.update(self._get_default_header())
        response = custom_requests.delete(
            self._get_api_url(
                constants.DELETE_CONVERSATION_API_ENDPOINT.format(
                    organization_uuid=organization_uuid,
                    conversation_uuid=conversation_uuid,
                )
            ),
            headers=header,
        )
        return response.ok

    def generate_conversation_title(
        self,
        organization_uuid: str,
        conversation_uuid: str,
        message: str,
        recent_conversation_names: List[str],
    ) -> Optional[JsonType]:
        """Generates a chat title for a given |conversation| in an |organization| when the current
        message is |message|, and the last few conversation names were |recent_conversation_names|.
        """
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.post(
            self._get_api_url(constants.GENERATE_CHAT_TITLE_API_ENDPOINT),
            headers=header,
            request_body={
                "organization_uuid": organization_uuid,
                "conversation_uuid": conversation_uuid,
                "message_content": message,
                "recent_titles": recent_conversation_names,
            },
        )
        if not response.ok:
            return None
        return response.json()

    def rename_conversation_title(self, organization_uuid: str, conversation_uuid: str, new_title: str) -> Optional[JsonType]:
        """Renames a conversation title to |new_title|."""
        request_body = {
            "organization_uuid": organization_uuid,
            "conversation_uuid": conversation_uuid,
            "title": new_title
        }
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.post(
            self._get_api_url(constants.RENAME_CONVERSATION_API_ENDPOINT),
            headers=header,
            request_body=request_body
        )
        if not response.ok:
            return None
        return response.json()

    def get_conversation_info(
        self, organization_uuid: str, conversation_uuid: str
    ) -> Optional[JsonType]:
        """Gets full chat information from an organization and chat uuid."""
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.get(
            self._get_api_url(
                constants.GET_CONVERSATION_INFO_API_ENDPOINT.format(
                    organization_uuid=organization_uuid,
                    conversation_uuid=conversation_uuid,
                )
            ),
            headers=header,
        )
        if not response.ok:
            return None
        return response.json()

    def get_conversations_from_org(self, organization_uuid: str) -> Optional[JsonType]:
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.get(
            self._get_api_url(
                constants.GET_CONVERSATIONS_API_ENDPOINT.format(
                    organization_uuid=organization_uuid
                )
            ),
            headers=header,
        )
        if not response.ok:
            return None
        return response.json()

    def get_organization_by_uuid(self, organization_uuid: str) -> Optional[JsonType]:
        """Gets an organization by its uuid."""
        organization_data = self.get_organizations()
        if organization_data is None:
            return None
        for organization in organization_data:  # type: ignore
            if organization["uuid"] == organization_uuid:
                return organization
        return None

    def get_organizations(self) -> Optional[JsonType]:
        """Get organization data JSON."""
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.get(
            self._get_api_url(constants.GET_ORGANIZATIONS_API_ENDPOINT), headers=header
        )
        if not response.ok:
            return None
        return response.json()

    def _send_message(
        self,
        organization_uuid: str,
        conversation_uuid: str,
        message: str,
        attachments: List,
        timezone: constants.Timezone,
        model: constants.Model,
    ) -> Iterator[JsonType]:
        """Sends a message to the given organization/conversation. Returns a generator that contains the streamed
        response output.
        """
        request_body = {
            "organization_uuid": organization_uuid,
            "conversation_uuid": conversation_uuid,
            "text": message,
            "attachments": attachments,
            "completion": {"prompt": message, "timezone": timezone, "model": model},
        }
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        if header["accept"]:
            header["accept"] += ",text/event-stream,text/event-stream"
        else:
            header["accept"] = "text/event-stream,text/event-stream"

        for streamed_data_chunk in custom_requests.sse(
            self._get_api_url(constants.APPEND_MESSAGE_API_ENDPOINT),
            headers=header,
            request_body=request_body,
        ):
            yield json.loads(streamed_data_chunk)

    def _get_api_url(self, endpoint: str):
        """Get the fully formed request URL."""
        return self._base_url + endpoint

    def _get_default_header(self) -> HeaderType:
        """Gets the default header with authentication, user agent, and other necessary header information."""
        defualt_header = {}
        defualt_header.update(self._spoofed_headers)
        defualt_header.update({"user-agent": self._user_agent})
        defualt_header.update({"cookie": f"sessionKey={self._session_key}"})
        return defualt_header
