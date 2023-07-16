import constants
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import custom_requests as requests
from custom_requests import JsonType

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
	def __init__(self, session_key: str, base_url: str = constants.BASE_URL, spoofed_headers: Optional[JsonType] = None):
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

		# Before calling any other methods, make sure that the key and the
		self._validate_params()

	####################################################################
	#                                                                  #
	#                         Public APIs                              #
	#                                                                  #
	####################################################################

	"""Generally speaking, this API returns and manages `Contexts`, which are
	representations of chats and organizations that the user is participating
	in.

	Users of the API are required to manage contexts on their own and pass them
	into methods when necessary. You can get an initial context by calling
	`create_conversation()`. From here, you can pass this context into
	`send_message()`.
	"""

	def send_message(self, conversation: ConversationContext, message: str) -> str:
		"""Main API. Sends a message to the claude API and returns the response that the API gave
		in string format.
		"""
		self._send_message(conversation.organization.uuid, conversation.uuid, message)

	def clear_conversations(
		self, organization: OrganizationContext
	) -> List[ConversationContext]:
		"""Clears all conversations in a given organization. Returns a list of
		conversations that could not be deleted.
		"""
		conversations = self._get_conversations_from_org(organization.uuid)

		non_deleted_convos = []
		for convo in conversations:
			if not self._delete_conversation_from_org(
				convo.organization.uuid, convo.uuid
			):
				non_deleted_convos.append(convo)

		return non_deleted_convos

	def delete_conversation(self, conversation: ConversationContext) -> bool:
		"""Deletes an existing conversation."""
		deleted = self._delete_conversation_from_org(
			conversation.organization.uuid, conversation.uuid
		)
		return deleted

	def get_conversations(
		self, organization: OrganizationContext
	) -> List[ConversationContext]:
		"""Gets a list of conversations that the user is in for a given organization."""
		conversations = self._get_conversations_from_org(organization.uuid)
		return conversations

	def get_organizations(self) -> List[OrganizationContext]:
		"""Gets a list of the organizations that the user is in."""
		organizations = self._get_organization_data()
		return organizations


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
		timezone: constants.Timezone = constants.Timezone.LA,
		model: constants.Model = constants.Model.CLAUDE_2,
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
		print(json.dumps(request_body))
		print()

		header = self._get_request_header()
		header["accept"] = "text/event-stream,text/event-stream"
		print(header)

		response = self._request_internal(
			constants.APPEND_MESSAGE_API_ENDPOINT,
			request_type=RequestType.POST,
			request_body=request_body,
			custom_header=header,
		)
		print(response)


	def _get_conversations_from_org(
		self, organization_uuid: str
	) -> List[ConversationContext]:
		"""Gets metadata about a users conversations in a particular organization."""
		response = self._request_internal(
			constants.CHAT_CONVERSATIONS_API_ENDPOINT.format(
				organization_uuid=organization_uuid
			),
			request_type=RequestType.GET,
		)
		response_json = response.json()

		conversations = []

		for conversation in response_json:
			conversations.append(
				ConversationContext(
					uuid=conversation["uuid"],
					name=conversation["name"],
					summary=conversation["summary"],
				)
			)

		return conversations


	def _delete_conversation_from_org(
		self, organization_uuid: str, conversation_uuid: str
	) -> bool:
		"""Removes a conversation |conversation_uuid| from the organization |organization_uuid|."""
		delete_endpoint = (
			constants.CHAT_CONVERSATIONS_API_ENDPOINT.format(
				organization_uuid=organization_uuid
			)
			+ f"/{conversation_uuid}"
		)
		response = self._request_internal(
			delete_endpoint,
			request_type=RequestType.DELETE,
			custom_header={"cookie": f"sessionKey={self._session_key}"},
		)
		return response.ok

	def _get_organization_data(self) -> List[OrganizationContext]:
		"""Get metadata about the users' organizations."""
		response = self._request_internal(
			constants.ORGANIZATIONS_API_ENDPOINT, request_type=RequestType.GET
		)
		if not response.ok:
			raise RuntimeError('Organization Data Response invalid.')

		response_json = response.json()
		assert len(response_json) > 0, "User is in Zero organizations."

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
		request_body: Optional[Dict[str, Any]] = None,
		custom_header: Optional[Dict[str, Any]] = None,
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
			response = requests.post(full_url, headers=header, request_body=request_body)
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

	def _attach_necessary_headers(self, input_headers: Optional[JsonType]) -> JsonType:
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
		assert self._base_url == constants.BASE_URL, "Base URL is invalid."
