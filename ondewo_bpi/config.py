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

# load default configuration from the environment
load_dotenv("./bpi.env")

PORT: str = os.getenv("PORT", "50051")
CAI_HOST: Optional[str] = os.getenv("CAI_HOST")
CAI_PORT: Optional[str] = os.getenv("CAI_PORT")
CAI_TOKEN: Optional[str] = os.getenv("CAI_TOKEN")
HTTP_AUTH_TOKEN: Optional[str] = os.getenv("HTTP_BASIC_AUTH")
USER_NAME: Optional[str] = os.getenv("USER_NAME")
USER_PASS: Optional[str] = os.getenv("USER_PASS")
SECURE: Optional[str] = os.getenv("SECURE")

config_path: str = os.getenv("CONFIG_PATH", "/home/ondewo/config.json")

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
        client_configuration_str = (
            "\nnlu-client configuration:\n"
            + f"   Secure: {SECURE}\n"
            + f"   Host: {CAI_HOST}\n"
            + f"   Port: {CAI_PORT}\n"
            + f"   Http_token: {HTTP_AUTH_TOKEN}\n"
            + f"   User_name: {USER_NAME}\n"
            + f"   Password: {USER_PASS}\n"
        )
        logger_console.info(client_configuration_str)

    def instantiate_client(self, cai_port: str = "") -> Tuple[ClientConfig, Client]:
        if cai_port == "":
            trial_port = CAI_PORT
            if trial_port == "" or not trial_port:
                trial_port = "50055"
            cai_port = trial_port

        if SECURE == "True":
            with open(config_path, "r") as fi:
                json_dict: Dict = json.load(fi)

            logger.info("configuring secure connection")
            config: ClientConfig = ClientConfig(
                host=CAI_HOST,
                port=cai_port,
                http_token=HTTP_AUTH_TOKEN,
                user_name=USER_NAME,
                password=USER_PASS,
                grpc_cert=json_dict["grpc_cert"],
            )
            client = Client(config=config)
        else:
            logger.info("configuring INSECURE connection")
            config = ClientConfig(
                host=CAI_HOST,
                port=cai_port,
                http_token=HTTP_AUTH_TOKEN,
                user_name=USER_NAME,
                password=USER_PASS,
            )
            client = Client(config=config, use_secure_channel=False)
        return config, client

    def get_client(self, cai_port: str = "") -> Client:
        if not self._built:
            self.config, self.client = self.instantiate_client(cai_port=cai_port)
            self._built = True
        return self.client
