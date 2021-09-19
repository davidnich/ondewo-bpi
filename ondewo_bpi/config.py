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

import json
import os
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv
from ondewo.nlu.client import Client
from ondewo.nlu.client_config import ClientConfig
from ondewo.logging.logger import logger, logger_console

import ondewo_bpi.__init__ as file_anchor

parent = os.path.abspath(os.path.join(os.path.dirname(file_anchor.__file__), os.path.pardir))

class CentralClientProvider:
    """
    provide a central nlu-client instance to the bpi server without building it on import
    """

    def __init__(self) -> None:
        self.config = None
        self.client = None
        self._built = False
        self._init_defaults()

    def _init_defaults(self) -> None:
        load_dotenv("./bpi.env")

        self.port: str = os.getenv("PORT", "50051")
        self.cai_host: Optional[str] = os.getenv("self.cai_host")
        self.cai_port: Optional[str] = os.getenv("self.cai_port")
        self.cai_token: Optional[str] = os.getenv("CAI_TOKEN")
        self.http_token: Optional[str] = os.getenv("HTTP_BASIC_AUTH")
        self.user_name: Optional[str] = os.getenv("self.user_name")
        self.user_pass: Optional[str] = os.getenv("self.user_pass")
        self.secure: Optional[str] = os.getenv("self.secure")

        self.config_path: str = os.getenv("CONFIG_PATH", "/home/ondewo/config.json")

        client_configuration_str = (
            "\nnlu-client configuration:\n"
            + f"   Secure: {self.secure}\n"
            + f"   Host: {self.cai_host}\n"
            + f"   Port: {self.cai_port}\n"
            + f"   Http_token: {self.http_token}\n"
            + f"   User_name: {self.user_name}\n"
            + f"   Password: {self.user_pass}\n"
        )
        logger_console.info(client_configuration_str)

    def get_port(self) -> int:
        return self.port

    def instantiate_client(self, cai_port: str = "") -> Tuple[ClientConfig, Client]:
        if cai_port == "":
            trial_port = self.cai_port
            if trial_port == "" or not trial_port:
                trial_port = "50055"
            cai_port = trial_port

        if self.secure == "True":
            with open(config_path, "r") as fi:
                json_dict: Dict = json.load(fi)

            logger.info("configuring secure connection")
            config: ClientConfig = ClientConfig(
                host=self.cai_host,
                port=cai_port,
                http_token=self.http_token,
                user_name=self.user_name,
                password=self.user_pass,
                grpc_cert=json_dict["grpc_cert"],
            )
            client = Client(config=config)
        else:
            logger.info("configuring INself.secure connection")
            config = ClientConfig(
                host=self.cai_host,
                port=cai_port,
                http_token=self.http_token,
                user_name=self.user_name,
                password=self.user_pass,
            )
            client = Client(config=config, use_secure_channel=False)
        return config, client

    def get_client(self, cai_port: str = "") -> Client:
        if not self._built:
            self.config, self.client = self.instantiate_client(cai_port=cai_port)
            self._built = True
        return self.client
