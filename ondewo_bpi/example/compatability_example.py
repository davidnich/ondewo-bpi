import os

from google.protobuf.json_format import MessageToJson
from ondewo.nlu import session_pb2
from ondewo.logging.logger import logger_console

from ondewo_bpi.bpi_server import BpiServer
from ondewo_bpi.config import CAI_PORT
from ondewo_bpi.example.login_mock import MockUserLoginServer, PortChecker
from ondewo_bpi.message_handler import MessageHandler
import grpc
from ondewo_bpi.helpers import add_params_to_cai_context

class UpdateServer(BpiServer):

    def __init__(self) -> None:
        os.environ["MODULE_NAME"] = "bpi_update_server"  # update module name for logger
        port_in_use = PortChecker.check_client_users_stub(port=CAI_PORT)
        if not port_in_use:
            self.mock_login_server = MockUserLoginServer()
            self.mock_login_server.serve(port=CAI_PORT)  # start mock-login server
        super().__init__()  # BpiServer.__init__() triggers Client-init and Login() grpc call
        if not port_in_use:
            self.mock_login_server.kill_server()  # kill mock-login server
        self.register_handlers()


    def register_handlers(self) -> None:
        self.register_intent_handler(
            intent_name="Default Fallback Intent", handler=self.handle_default_fallback,
        )
        self.register_intent_handler(
            intent_name="i.order.pizza", handler=self.handle_order_pizza,
        )

    @staticmethod
    def handle_default_fallback(response: session_pb2.DetectIntentResponse) -> session_pb2.DetectIntentResponse:
        logger_console.warning("Default fallback was triggered!")
        return response

    @staticmethod
    def handle_order_pizza(response: session_pb2.DetectIntentResponse) -> session_pb2.DetectIntentResponse:
        logger_console.warning(f"Order pizza .. RESPONSE was {list(response.query_result.fulfillment_messages)}")
        return response


if __name__ == "__main__":
    server = UpdateServer()
    server.serve()