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

import pytest  # noqa:

from ondewo_bpi.bpi_server import BpiServer
from ondewo_bpi.config import Client

# from ondewo.nlu import session_pb2_grpc


def test_import() -> None:
    bpi = BpiServer()
    assert isinstance(bpi.client, Client)
    assert isinstance(bpi.intent_handlers, list)
    assert not bpi.server
