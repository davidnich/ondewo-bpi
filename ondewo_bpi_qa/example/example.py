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

from ondewo.nlu import session_pb2
from ondewo.logging.logger import logger_console

from ondewo_bpi_qa.bpi_qa_server import QAServer


class MyQAServer(QAServer):
    def __init__(self) -> None:
        super().__init__()

    def register_intent_handlers(self) -> None:
        self.register_intent_handler(
            intent_pattern="Default Fallback Intent", handlers=[self.handle_default_fallback],
        )
        self.register_intent_handler(
            intent_pattern="Default Exit Intent", handlers=[self.handle_default_exit],
        )

    @staticmethod
    def handle_default_fallback(response: session_pb2.DetectIntentResponse) -> session_pb2.DetectIntentResponse:
        logger_console.warning("Default fallback was triggered!")
        return response

    @staticmethod
    def handle_default_exit(response: session_pb2.DetectIntentResponse) -> session_pb2.DetectIntentResponse:
        logger_console.warning("Default exit was triggered!")
        return response

    def serve(self) -> None:
        super().serve()


if __name__ == "__main__":
    server = MyQAServer()
    server.serve()
