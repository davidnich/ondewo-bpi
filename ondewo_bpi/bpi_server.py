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
from concurrent import futures
from typing import List, Optional

import grpc
from grpc_reflection.v1alpha import reflection
from ondewo.nlu import (
    agent_pb2,
    entity_type_pb2,
    aiservices_pb2,
    project_role_pb2,
    intent_pb2,
    session_pb2,
    session_pb2_grpc,
    user_pb2,
    user_pb2_grpc,
    context_pb2,
    context_pb2_grpc,
    agent_pb2_grpc,
    entity_type_pb2_grpc,
    intent_pb2_grpc,
    aiservices_pb2_grpc,
    project_role_pb2_grpc,
)
from ondewo.nlu.client import Client as NLUClient
from ondewo.logging.decorators import Timer
from ondewo.logging.logger import logger, logger_console

from ondewo_bpi.bpi_services import BpiSessionsServices, BpiUsersServices, BpiContextServices, \
    BpiAgentsServices, BpiEntityTypeServices, BpiAiServicesServices, BpiIntentsServices, \
    BpiProjectRolesServices
from ondewo_bpi.config import PORT, CentralClientProvider


class BpiServer(
    BpiAgentsServices,
    BpiAiServicesServices,
    BpiContextServices,
    BpiEntityTypeServices,
    BpiIntentsServices,
    BpiProjectRolesServices,
    BpiSessionsServices,
    BpiUsersServices,
):
    @property
    def client(self) -> NLUClient:
        return self._client

    @client.setter
    def client(self, value: NLUClient) -> None:
        self._client = value

    def __init__(self, client_provider: Optional[CentralClientProvider]) -> None:
        super().__init__()
        if not client_provider:
            self.client = CentralClientProvider().get_client()
        else:
            self.client = client_provider.get_client()
        self.server = None
        self.services_descriptors: List[str] = [
            agent_pb2.DESCRIPTOR.services_by_name["Agents"].full_name,  # type: ignore
            context_pb2.DESCRIPTOR.services_by_name["Contexts"].full_name,  # type: ignore
            entity_type_pb2.DESCRIPTOR.services_by_name["EntityTypes"].full_name,  # type: ignore
            intent_pb2.DESCRIPTOR.services_by_name["Intents"].full_name,  # type: ignore
            session_pb2.DESCRIPTOR.services_by_name["Sessions"].full_name,  # type: ignore
            aiservices_pb2.DESCRIPTOR.services_by_name["AiServices"].full_name,  # type: ignore
            project_role_pb2.DESCRIPTOR.services_by_name["ProjectRoles"].full_name,  # type: ignore
            user_pb2.DESCRIPTOR.services_by_name["Users"].full_name,  # type: ignore
        ]

    def _setup_reflection(self) -> None:
        reflection.enable_server_reflection(service_names=self.services_descriptors, server=self.server)

    def _add_services(self) -> None:
        agent_pb2_grpc.add_AgentsServicer_to_server(self, self.server)
        context_pb2_grpc.add_ContextsServicer_to_server(self, self.server)
        entity_type_pb2_grpc.add_EntityTypesServicer_to_server(self, self.server)
        intent_pb2_grpc.add_IntentsServicer_to_server(self, self.server)
        session_pb2_grpc.add_SessionsServicer_to_server(self, self.server)
        aiservices_pb2_grpc.add_AiServicesServicer_to_server(self, self.server)
        project_role_pb2_grpc.add_ProjectRolesServicer_to_server(self, self.server)
        user_pb2_grpc.add_UsersServicer_to_server(self, self.server)

    @Timer(log_arguments=False)
    def _setup_server(self) -> None:
        logger.info("attempting to setup server...")
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self._add_services()
        self._setup_reflection()
        self.server.add_insecure_port(f"[::]:{PORT}")  # type: ignore
        logger.info(f"SERVING SERVER AT SERVING PORT {PORT}")
        self.server.start()  # type: ignore

    def serve(self) -> None:
        logger_console.info(f"attempting to start server on port {PORT}")
        self._setup_server()
        logger_console.warning({"message": f"Server started on port {PORT}", "content": PORT})
        logger_console.warning(
            {
                "message": f"using intent handlers dict {list(self.intent_handlers.keys())}",
                "content": list(self.intent_handlers.keys()),
            }
        )
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger_console.info("Keyboard interrupt, shutting down")
        logger_console.info({"message": "server shut down", "tags": ["timing"]})