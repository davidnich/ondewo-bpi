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

from autocode.client_type import ClientType
from autocode.grpc_auto_coder import GRPCAutoCoder

# TODO: Make it dynamic so it reads from the file system

files_to_generate = [
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/user_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/user_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/user.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/users.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/session_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/session_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/session.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/sessions.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/context_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/context_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/context.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/contexts.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/agent_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/agent_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/agent.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/agents.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/entity_type_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/entity_type_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/entity_type.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/entity_types.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/intent_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/intent_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/intent.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/intents.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/aiservices_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/aiservices_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/aiservices.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/aiservices.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/nlu/project_role_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/project_role_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/nlu/project_role.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/nlu/services/project_roles.py",
        "client_type": ClientType.NLU,
    },
    {
        "in_file": "./ondewo-nlu-client-python/ondewo/qa/qa_pb2_grpc.py",
        "out_file": "./ondewo_bpi/autocoded/qa_grpc_autocode.py",
        "proto_file": "./ondewo-nlu-client-python/ondewo-nlu-api/ondewo/qa/qa.proto",
        "client_file": "./ondewo-nlu-client-python/ondewo/qa/services/qa.py",
        "client_type": ClientType.QA,
    },
]


if __name__ == "__main__":

    for file_dic in files_to_generate:
        coder = GRPCAutoCoder(
            in_file=file_dic["in_file"],
            out_file=file_dic["out_file"],
            proto_file=file_dic["proto_file"],
            client_file=file_dic["client_file"],
            client_type=file_dic["client_type"],
        )
        coder.generate_code()
