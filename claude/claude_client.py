"""Helper class to access Claude APIs via raw json."""
import json
import pathlib
from typing import List, Optional, Iterator, Union


from claude import constants
from claude import custom_requests
from claude import helpers
from claude.custom_types import JsonType, HeaderType, AttachmentType
from claude import logger

# Logging levels.
LOG_LEVEL_DEBUG = logger.logger.DEBUG
LOG_LEVEL_INFO = logger.logger.INFO
LOG_LEVEL_WARNING = logger.logger.WARNING
LOG_LEVEL_ERROR = logger.logger.ERROR

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
        logging_level: int = LOG_LEVEL_WARNING,
    ):
        self._session_key = session_key
        self._base_url = base_url
        self._user_agent = user_agent
        if spoofed_headers is None:
            self._spoofed_headers = constants.HEADERS
        else:
            self._spoofed_headers = spoofed_headers

        logger.logger.getLogger().setLevel(logging_level)

    def send_message(
        self,
        organization_uuid: str,
        conversation_uuid: str,
        message: str,
        attachments: List[AttachmentType],
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
            STOP_SEQUENCE = 'stop_sequence'
            aggregated_completion = []
            final_response = None
            for elem in self._send_message(
                organization_uuid,
                conversation_uuid,
                message,
                attachments,
                timezone,
                model,
            ):
                final_response = elem
                # Make sure that the completion text is in the json chunks.
                if 'completion' in elem:
                    # The new API sends each chunk of text in the `completion` field, and
                    # it has to be stiched together at the end to form the full response.
                    aggregated_completion.append(elem['completion'])
                # Return early if we hit the stop sequence, though this may not be correct
                # 100% of the time.
                if 'stop_reason' in elem and elem['stop_reason'] == STOP_SEQUENCE:
                    break
            # If we never set the final response, that means that we had no response.
            # In this case, return None.
            if final_response is None:
                logger.logger.warning("Response from sending message is None.")
                return None
            # Return the response as if it were the full json response, but replace
            # the `completion` section with the aggregated completion.
            final_response['completion'] = ''.join(aggregated_completion)
            return final_response

    def convert_file(
        self, organization_uuid: str, file_path: str
    ) -> Optional[AttachmentType]:
        """Uploads a file to the claude API to convert it into an attatchment type. The return
        type for this method can be directly sent as an attachment in send_message() calls.

        The actual schema of the return json can be found under custom_types.py
        """
        pathlib_file = pathlib.Path(file_path)
        if not pathlib_file.is_file():
            logger.logger.warning("Path %s does not exist.", file_path)
            return None
        # If the file is text based, directly read the file contents and return an attachment for it.
        is_text_based, contents = helpers.is_file_text_based(file_path)
        if is_text_based:
            logger.logger.info("Text based file detected, not converting.")
            if contents is None:
                logger.logger.warning("Contents of file in %s is not unicode decodable.", file_path)
                return None
            return { # type: ignore
                "file_name": pathlib_file.name,
                "file_type": pathlib_file.suffix,
                "file_size": len(contents),
                "extracted_content": contents,
            }

        # If the file is not text based, upload the file to the claude API, and then receive
        # the attachment in response.
        logger.logger.info("Uploading non-text based file %s to API endpoint.", file_path)
        form_data = {
            "orgUuid": organization_uuid,
            "file": (file_path, open(file_path, "rb")),
        }
        header = {}
        header.update(self._get_default_header())
        response = custom_requests.post_form_data(
            self._get_api_url(constants.CONVERT_DOCUMENT_API_ENDPOINT), headers=header, files=form_data
        )
        if not response.ok:
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
        return response.json() # type: ignore

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
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
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

        logger.logger.info("Response json object: %s", str(response))
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
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
        return response.json()

    def rename_conversation_title(
        self, organization_uuid: str, conversation_uuid: str, new_title: str
    ) -> Optional[JsonType]:
        """Renames a conversation title to |new_title|."""
        request_body = {
            "organization_uuid": organization_uuid,
            "conversation_uuid": conversation_uuid,
            "title": new_title,
        }
        header = {}
        header.update(self._get_default_header())
        header.update({"content-type": "application/json"})
        response = custom_requests.post(
            self._get_api_url(constants.RENAME_CONVERSATION_API_ENDPOINT),
            headers=header,
            request_body=request_body,
        )
        if not response.ok:
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
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
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
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
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
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
            logger.logger.warning("Failed response object: %s", str(response))
            return None

        logger.logger.info("Response json object: %s", str(response.json()))
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
