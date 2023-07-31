from typing import Optional, List, Dict
import uuid

from claude import constants
from claude import claude_client
from claude.custom_types import JsonType, AttachmentType


class ClaudeWrapper:
    """Wrapper around the raw API that makes it easy to talk in a given organization.

    Takes in a Claude Client and the organization that the client should use. Can optionally
    `switch conversation contexts` to persist a certain conversation uuid and omit passing
    in a conversation uuid on every method call.
    """

    def __init__(self, client: claude_client.ClaudeClient, organization_uuid: Optional[str] = None):
        """Initialize the wrapper with a client and an optional organization_uuid. If an organization uuid
        isn't provided, the wrapper will automatically use the first organization in the list of organizations
        that the user is in.
        """
        self._client = client
        if organization_uuid is None:
            self._organization_uuid = self._client.get_organizations()[0]['uuid']  # type: ignore
        else:
            self._organization_uuid = organization_uuid

        self._current_conversation = None

    ####################################################################
    #                                                                  #
    #                         Public APIs                              #
    #                                                                  #
    ####################################################################

    def send_message(
        self,
        message: str,
        attachments: List[AttachmentType] = [],
        conversation_uuid: Optional[str] = None,
        timezone: constants.Timezone = constants.Timezone.LA,
        model: constants.Model = constants.Model.CLAUDE_2,
    ) -> Optional[JsonType]:
        """Sends a message to the provided |conversation_uuid|, if one is provided. If none
        is provided, falls back to using the current conversation context. Otherwise,
        returns None.

        Returns the JSON repsonse of claude in response to the message.
        """
        conversation_to_use = self._get_conversation_or_context(conversation_uuid)
        if conversation_to_use is None:
            return None

        return self._client.send_message(  # type: ignore
            self._organization_uuid,
            conversation_to_use,
            message,
            attachments,
            timezone,
            model,
            stream=False,
        )
    
    def get_attachment(self, file_path: str) -> Optional[AttachmentType]:
        """Returns an attachment type for a passed in |file_path|. AttachmentTypes can be sent
        as part of the |attachment| argument in send_message().
        """
        return self._client.convert_file(self._organization_uuid, file_path)

    def start_new_conversation(
        self,
        conversation_name: str,
        initial_message: str = "",
        initial_attachments: List[AttachmentType] = [],
        timezone: constants.Timezone = constants.Timezone.LA,
        model: constants.Model = constants.Model.CLAUDE_2,
    ) -> Optional[Dict[str, str]]:
        """Creates a new conversation with |conversation_name| and initiates the conversation
        with an initial message |initial_message|, and optionally an initial set of attachments
        in |initial_attachments|.

        Returns a json with the uuid of the newly created chat, the response from creating the title
        for the new chat, and the title of the new chat, in a json formatted like:
        {
            'uuid': {conversation_uuid: str},
            'title': {chat_title: str},
            'response': {initial message response: Json}
        }
        """
        conversation_uuid = str(uuid.uuid4())

        # First, create the new conversation under the organization, and with the new conversation uuid.
        # If this doesn't work, return early.
        create_convo_result = self._client.create_conversation(
            self._organization_uuid, conversation_uuid
        )
        if create_convo_result is None:
            return None

        send_init_message_result = {}
        if initial_message:
            # Send the initial message to the newly created conversation.
            send_init_message_result = self._client.send_message(
                self._organization_uuid,
                conversation_uuid,
                initial_message,
                initial_attachments,
                timezone,
                model,
                stream=False,
            )
            if send_init_message_result is None:
                return None

        # Generate a title for the new chat based on the names of previous chats.
        recent_conversation_names = []
        conversations = self._client.get_conversations_from_org(self._organization_uuid)
        if conversations is not None:
            recent_conversation_names.extend([convo["name"] for convo in conversations])  # type: ignore
        else:
            # If we can't generate a title, just use the conversation name the user provided.
            recent_conversation_names = [conversation_name]

        convo_title = self._client.generate_conversation_title(
            self._organization_uuid,
            conversation_uuid,
            initial_message,
            recent_conversation_names,
        )
        if convo_title is None:
            return None

        return { # type: ignore
            'uuid': conversation_uuid,
            'title': convo_title['title'], # type: ignore
            'response': send_init_message_result # type: ignore
        }

    def rename_conversation(
        self, new_title: str, conversation_uuid: Optional[str] = None
    ) -> Optional[JsonType]:
        """Renames a conversation to |new_title|."""
        conversation_to_use = self._get_conversation_or_context(conversation_uuid)
        if conversation_to_use is None:
            return None
        response = self._client.rename_conversation_title(
            self._organization_uuid, conversation_to_use, new_title
        )
        if response is None:
            return None
        return response

    def get_conversation_info(
        self, conversation_uuid: Optional[str] = None
    ) -> Optional[JsonType]:
        """Gets the message history for a |conversation_uuid| or the current context."""
        conversation_to_use = self._get_conversation_or_context(conversation_uuid)
        if conversation_to_use is None:
            return None
        return self._client.get_conversation_info(
            self._organization_uuid, conversation_to_use
        )

    def delete_all_conversations(self) -> List[str]:
        """Deletes all the conversations in the organization. Returns a list of conversations uuids
        that the client failed to delete. In the case that all conversations were deleted correctly,
        this should return an empty list.
        """
        failed_deletion = []
        conversations = self._client.get_conversations_from_org(self._organization_uuid)
        for conversation in conversations:  # type: ignore
            if not self.delete_conversation(conversation["uuid"]):
                failed_deletion.append(conversation["uuid"])
        return failed_deletion

    def delete_conversation(self, conversation_uuid: Optional[str] = None) -> bool:
        """Deletes the provided conversation uuid or the current conversation context.
        Returns true if the conversation was deleted correctly.
        """
        conversation_to_use = self._get_conversation_or_context(conversation_uuid)
        if conversation_to_use is None:
            return False

        conversation_deleted = self._client.delete_conversation(
            self._organization_uuid, conversation_to_use
        )
        # If we deleted the current conversation context, clear it from our state so that we can't use it again.
        if conversation_deleted and conversation_to_use == self._current_conversation:
            self.clear_conversation_context()
        return conversation_deleted

    def get_conversations(self) -> Optional[JsonType]:
        """Gets a json dictionary of all the conversations in the current organization."""
        return self._client.get_conversations_from_org(self._organization_uuid)

    def set_conversation_context(self, conversation_uuid: str) -> None:
        """Sets the current conversation conext to |conversation_uuid|.
        Useful for if you don't want to constantly pass a conversation uuid
        to every method call.
        """
        self._current_conversation = conversation_uuid

    def clear_conversation_context(self) -> None:
        """Clears the current conversation context."""
        self._current_conversation = None

    def switch_client(self, new_client: claude_client.ClaudeClient, organization_uuid: Optional[str] = None) -> None:
        """Switches the current client to a new client. Can optionally provide an |organization_uuid|,
        otherwise we will infer the organization uuid to be the first uuid in the list or organizations
        that the client is in.
        """
        self._client = new_client
        if organization_uuid is None:
            self._organization_uuid = self._client.get_organizations()[0]['uuid']  # type: ignore
        else:
            self._organization_uuid = organization_uuid

        self._current_conversation = None        

    ####################################################################
    #                                                                  #
    #                       Helper Methods                             #
    #                                                                  #
    ####################################################################

    def _get_conversation_or_context(
        self, override_conversation: Optional[str]
    ) -> Optional[str]:
        """Returns what conversation to use - the overriden context, or the current conversation
        context.
        """
        conversation_to_use = self._current_conversation
        if override_conversation is not None:
            conversation_to_use = override_conversation
        if conversation_to_use is None:
            return None
        return conversation_to_use
