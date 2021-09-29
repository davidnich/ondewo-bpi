# Copyright 2021 ONDEWO GmbH
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import functools
from abc import ABCMeta, abstractmethod
from typing import Dict, Callable, List, Optional, Any
import regex as re
import grpc
from ondewo.nlu import session_pb2, intent_pb2, user_pb2, context_pb2
from ondewo.nlu.client import Client as NLUClient
from ondewo.logging.decorators import Timer
from ondewo.logging.logger import logger_console
from ondewo.nlu.intent_pb2 import ListIntentsRequest, IntentView, Intent

from ondewo_bpi.autocoded.agent_grpc_autocode import AutoAgentsServicer
from ondewo_bpi.autocoded.aiservices_grpc_autocode import AutoAiServicesServicer
from ondewo_bpi.autocoded.context_grpc_autocode import AutoContextsServicer
from ondewo_bpi.autocoded.entity_type_grpc_autocode import AutoEntityTypesServicer
from ondewo_bpi.autocoded.intent_grpc_autocode import AutoIntentsServicer
from ondewo_bpi.autocoded.project_role_grpc_autocode import AutoProjectRolesServicer
from ondewo_bpi.autocoded.session_grpc_autocode import AutoSessionsServicer
from ondewo_bpi.autocoded.user_grpc_autocode import AutoUsersServicer
from ondewo_bpi.constants import SipTriggers, QueryTriggers
from ondewo_bpi.message_handler import MessageHandler, SingleMessageHandler

from ondewo_bpi.helpers import get_session_from_response
from collections import OrderedDict


class BpiSessionsServices(AutoSessionsServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass

    def __init__(self) -> None:

        self.intent_handlers: Dict[str,List[Callable]] = OrderedDict()
        self.trigger_handlers: Dict[str, Callable] = {
            i.value: self.trigger_function_not_implemented for i in [*SipTriggers, *QueryTriggers]
        }

    def register_intent_handler(self, intent_name: str, handlers: List[Callable]) -> None:
        self.intent_handlers[intent_name] = handlers
        # Make sure they are ordered by key length on insert
        self.intent_handlers = self._create_ordered_dict_by_key_value_length(
            dictionary=self.intent_handlers
        )

    def register_trigger_handler(self, trigger: str, handler: Callable) -> None:
        self.trigger_handlers[trigger] = handler

    def trigger_function_not_implemented(
            self,
            response: session_pb2.DetectIntentResponse,
            message: intent_pb2.Intent.Message,
            trigger: str,
            found_triggers: Dict[str, List[str]],
    ) -> None:
        logger_console.warning(
            {
                "message": f"no function for the trigger {trigger}, please subclass and implement",
                "trigger": trigger,
                "content": found_triggers[trigger],
            }
        )

    def DetectIntent(
            self, request: session_pb2.DetectIntentRequest, context: grpc.ServicerContext
    ) -> session_pb2.DetectIntentResponse:
        try:
            text = request.query_input.text.text
        except Exception:
            logger_console.exception("something wrong in the bpi")
            text = "error"
        logger_console.warning(
            {
                "message": f"CAI-DetectIntentRequest to CAI, text input: {text}",
                "content": text,
                "text": text,
                "tags": ["text"],
            }
        )
        cai_response = self.perform_detect_intent(request)
        intent_name = cai_response.query_result.intent.display_name
        logger_console.warning(
            {
                "message": f"CAI-DetectIntentResponse from CAI, intent_name: {intent_name}",
                "content": intent_name,
                "intent_name": intent_name,
                "session_id": get_session_from_response(cai_response),
                "tags": ["text"],
            }
        )

        cai_response = self.process_messages(cai_response)
        return self.process_intent_handler(cai_response)

    @Timer(log_arguments=False, recursive=True)
    def perform_detect_intent(self,
                              request: session_pb2.DetectIntentRequest, ) -> session_pb2.DetectIntentResponse:
        return self.client.services.sessions.detect_intent(request)

    @Timer(log_arguments=False, recursive=True)
    def process_messages(self,
                         response: session_pb2.DetectIntentResponse, ) -> session_pb2.DetectIntentResponse:
        new_response = None
        for j, message in enumerate(response.query_result.fulfillment_messages):
            found_triggers = MessageHandler.get_triggers(message, get_session_from_response(response))

            for found_trigger in found_triggers:
                new_response = self.trigger_handlers[found_trigger](response, message, found_trigger,
                                                                    found_triggers)
                if new_response:
                    if not new_response.response_id == response.response_id:
                        return new_response

            for found_trigger in found_triggers:
                SingleMessageHandler.substitute_pattern_in_message(message, found_trigger, "")

            self.quicksend_to_api(response, message, j)
        if not len(response.query_result.fulfillment_messages):
            self.quicksend_to_api(response, None, 0)
        return response

    def quicksend_to_api(
            self, response: session_pb2.DetectIntentResponse, message: Optional[intent_pb2.Intent.Message],
            count: int
    ) -> None:
        logger_console.warning({"message": "quicksend_to_api not written, please subclass and implement"})

    @Timer(log_arguments=False, recursive=True)
    def process_intent_handler(
            self, cai_response: session_pb2.DetectIntentResponse
    ) -> session_pb2.DetectIntentResponse:
        # Create an ordered dictionary by key value length
        intent_name = cai_response.query_result.intent.display_name
        handlers: Optional[List[Callable]] = self._get_handlers_for_intent(intent_name, self.intent_handlers)
        if handlers is not None:
            for handler in handlers:
                cai_response = handler(cai_response)
                text = [i.text.text for i in cai_response.query_result.fulfillment_messages]
                logger_console.warning(
                    {
                        "message": f"BPI-DetectIntentResponse from BPI with text: {text}",
                        "content": text,
                        "text": text,
                        "tags": ["text", "clean"],
                    }
                )
        return cai_response

    def _create_ordered_dict_by_key_value_length(self, dictionary: Dict) -> Dict:
        return OrderedDict(sorted(dictionary.items(), key=lambda x: len(x[0]), reverse=True))

    @functools.lru_cache(maxsize=20)
    def _get_handlers_for_intent(self, intent_name, sorted_dict: Dict[str,Any]) -> Optional[List[Callable]]:
        for key in sorted_dict.keys():
            if re.match(key, intent_name):
                return sorted_dict.get(key)
        return None


class BpiUsersServices(AutoUsersServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass

    def Login(self, request: user_pb2.LoginRequest, context: grpc.ServicerContext) -> user_pb2.LoginResponse:
        logger_console.info("login request handled by bpi")
        return user_pb2.LoginResponse(auth_token=self.client.services.users.metadata[0][1])


class BpiContextServices(AutoContextsServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass

    def CreateContext(
            self, request: context_pb2.CreateContextRequest, context: grpc.ServicerContext
    ) -> context_pb2.Context:
        logger_console.info("passing create context request on to CAI")
        return self.client.services.contexts.create_context(request=request)


class BpiAgentsServices(AutoAgentsServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass


class BpiEntityTypeServices(AutoEntityTypesServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass


class BpiAiServicesServices(AutoAiServicesServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass


class BpiIntentsServices(AutoIntentsServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass


class BpiProjectRolesServices(AutoProjectRolesServicer):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def client(self) -> NLUClient:
        pass
