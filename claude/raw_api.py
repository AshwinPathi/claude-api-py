"""Helper class to access Claude APIs via raw json."""
import json
from typing import List, Optional, Dict, Any, Iterator

from claude import constants
from claude import custom_requests
from claude.custom_requests import JsonType, HeaderType


class RawClaudeAPI:
    """Acts as a lower level interface to the Claude API. Returns raw JSON
    structs and accepts lower level arguments to manipulate the Claude API.
    """

    def __init__(
        self,
        session_key: str,
        base_url: str = constants.BASE_URL,
        spoofed_headers: Optional[HeaderType] = None,
    ):
        self._session_key = session_key
        self._base_url = base_url
        if spoofed_headers is None:
            self._spoofed_headers = {}
        else:
            self._spoofed_headers = spoofed_headers

    def send_message(
        self,
        organization_uuid: str,
        conversation_uuid: str,
        message: str,
        attachments: List,
        timezone: str,
        model: str,
    ) -> Iterator:
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
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        header.update({"content-type": "application/json"})
        if header["accept"]:
            header["accept"] += ",text/event-stream,text/event-stream"
        else:
            header["accept"] = "text/event-stream,text/event-stream"

        for streamed_data_chunk in custom_requests.sse(
            self._base_url + constants.APPEND_MESSAGE_API_ENDPOINT,
            headers=header,
            request_body=request_body,
        ):
            yield json.loads(streamed_data_chunk)

    def create_conversation(
        self, organization_uuid: str, new_conversation_uuid: str
    ) -> Optional[JsonType]:
        """Creates a conversation in the organization represented by |organization_uuid|,
        with a new conversation id of |new_conversation_uuid|.
        """
        header = {}
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.post(
            self._base_url
            + constants.START_CONVERSATION_API_ENDPOINT.format(
                organization_uuid=organization_uuid
            ),
            headers=header,
            request_body={"name": "", "uuid": new_conversation_uuid},
        )
        if not response.ok:
            return None
        return response.json()

    def delete_conversation(
        self, organization_uuid: str, conversation_uuid: str
    ) -> Optional[JsonType]:
        """Removes a conversation |conversation_uuid| from the organization |organization_uuid|."""
        header = {}
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        response = custom_requests.delete(
            constants.DELETE_CONVERSATION_API_ENDPOINT.format(
                organization_uuid=organization_uuid, conversation_uuid=conversation_uuid
            ),
            headers=header,
        )
        if not response.ok:
            return None
        return response.json()

    def generate_chat_title(
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
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.post(
            self._base_url + constants.GENERATE_CHAT_TITLE_API_ENDPOINT,
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

    def get_conversation_info(
        self, organization_uuid: str, conversation_uuid: str
    ) -> Optional[JsonType]:
        """Gets full chat information from an organization and chat uuid."""
        header = {}
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.get(
            self._base_url
            + constants.GET_CONVERSATION_INFO_API_ENDPOINT.format(
                organization_uuid=organization_uuid, conversation_uuid=conversation_uuid
            ),
            headers=header,
        )
        if not response.ok:
            return None
        return response.json()

    def get_conversations_from_org(self, organization_uuid: str) -> Optional[JsonType]:
        header = {}
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.get(
            self._base_url
            + constants.GET_CONVERSATIONS_API_ENDPOINT.format(
                organization_uuid=organization_uuid
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
        header.update(self._spoofed_headers)
        header.update(self._get_auth_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.get(
            self._base_url + constants.GET_ORGANIZATIONS_API_ENDPOINT, headers=header
        )
        if not response.ok:
            return None
        return response.json()

    def _get_auth_header(self) -> HeaderType:
        return {"cookie": f"sessionKey={self._session_key}"}
