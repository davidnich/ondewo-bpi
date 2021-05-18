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

import time
from typing import Dict, Optional, Tuple, Any

import grpc
from ondewo.nlu import intent_pb2, session_pb2
from ondewo.logging.decorators import Timer
from ondewo.logging.logger import logger_console
from ondewo.sip.client_config import SipClientConfig
from ondewo.sip.client import SipClient

import ondewo_bpi.helpers as helpers
from ondewo_bpi.bpi_server import BpiServer
from ondewo_bpi_sip.config import TIMEOUT_MINUTES


def get_flask_url_from_session_id(session: str) -> str:
    identifying_info = session.split("XXX")[1].split("-")
    return f"http://{identifying_info[0]}:{identifying_info[1]}/{identifying_info[2]}"


def get_sip_host_name_port_from_session_id(session: str) -> Tuple[str, Optional[str], str]:
    try:
        identifying_info = session.split("XXX")[1].split("-")
        if "None" in identifying_info[1]:
            return identifying_info[0], None, identifying_info[2]
        return identifying_info[0], identifying_info[1], identifying_info[2]
    except ValueError:
        return None, None, None


class SipServer(BpiServer):
    def __init__(self) -> None:
        super().__init__()
        self.session_information: Dict[str, Dict[str, Any]] = {
            "session_uuid": {"client": None, "timestamp": 0.0}
        }

    def DetectIntent(
        self, request: session_pb2.DetectIntentRequest, context: grpc.ServicerContext
    ) -> session_pb2.DetectIntentResponse:
        self.check_session(request)
        return super().DetectIntent(request=request, context=context)  # type: ignore

    @Timer(log_arguments=False)
    def check_session(self, request: session_pb2.DetectIntentRequest) -> None:
        if request.session not in self.session_information.keys():
            host, port, name = get_sip_host_name_port_from_session_id(request.session)
            if None in [host, port, name]:
                logger_console.warning(
                    "WARNING: Sip client not initialized correctly!"
                    " No responses will be sent!"
                )
                self.session_information[request.session] = {
                    "client": None,
                    "timestamp": time.time()
                }
            else:
                logger_console.warning(
                    f"Sip host: {host}:{port}/{name}"
                )
                config: SipClientConfig = SipClientConfig(
                    host=host,
                    port=port,
                    name=name,
                )

                sip_client: SipClient = SipClient(config=config)
                self.session_information[request.session] = {
                    "client": sip_client,
                    "timestamp": time.time()
                }
            logger_console.warning(
                "New session in bpi."
                f" {len(self.session_information)} sessions currently stored."
            )

        for session in self.session_information.copy():
            current_age = time.time() - self.session_information[session]["timestamp"]
            if current_age > (TIMEOUT_MINUTES * 60):
                logger_console.warning(
                    f"Popping old session: session = {session}"
                    f" timestamp = {self.session_information[session]['timestamp']}"
                    f" age = {current_age},"
                    f" timeout is {TIMEOUT_MINUTES} minutes."
                )
                self.session_information.pop(session)

    def quicksend_to_api(
        self, response: session_pb2.DetectIntentResponse, message: Optional[intent_pb2.Intent.Message], count: int,
    ) -> None:
        client = self.session_information[helpers.get_session_from_response(response)]["client"]
        if not client:
            logger_console.warning(
                "WARNING: Sip client not initialized correctly! No responses will be sent!"
            )
            return
        if not message:
            client.services.text_to_speech.send_text_get_filename(  # type: ignore
                text_to_send="", session_id=helpers.get_session_from_response(response), response_type="final"
            )
            return
        if not message.HasField("text"):
            client.services.text_to_speech.send_text_get_filename(  # type: ignore
                text_to_send="", session_id=helpers.get_session_from_response(response), response_type="final"
            )
            return
        if message.HasField("card"):
            client.services.text_to_speech.send_text_get_filename(  # type: ignore
                text_to_send="", session_id=helpers.get_session_from_response(response), response_type="final"
            )
            return
        is_final: bool = ((count + 1) == len(response.query_result.fulfillment_messages))
        client.services.text_to_speech.send_text_get_filename(  # type: ignore
            text_to_send=message.text.text[0],
            session_id=helpers.get_session_from_response(response),
            response_type="final" if is_final else "partial",
        )
