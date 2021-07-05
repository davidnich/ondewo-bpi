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

import regex as re
from typing import List, Tuple, Dict, Optional

from autocode.base_coder import ClassCoder, FunctionCoder
from autocode.client_type import ClientType


class GRPCAutoCoder:
    """
    code-generator class to
        1) get endpoint function names from auto-generated grpc python file
        2) get endpoint information like request and response types and message names from .proto file
        3) get client function information by comparing endpoint information with client functions
        4) generate metaclass for grpc-server subclassing which relays requests to appropriate client functions

    Arguments:
        in_file: input python path+filename to get endpoint functions from
        out_file: export name+path of generated python file
        proto_file: base .proto file with rpc endpoint definitions, from which in_file was generated
        client_file: ondewo.nlu.client file for the client functions associated with in_file

    Example:
        in_file = "./ondewo-nlu-client-python/ondewo/nlu/user_pb2_grpc.py"
        out_file = f"./{__file__.split('/')[-2]}/generated.py"
        proto_file = "./ondewo-nlu-client-python/ondewoapis/ondewo/nlu/user.proto"
        client_file = "./ondewo-nlu-client-python/ondewo/nlu/services/users.py"
    """

    def __init__(
            self,
            in_file: str,
            out_file: str,
            proto_file: str,
            client_file: str,
            client_type: ClientType
    ):
        self.in_file = in_file
        self.out_file = out_file
        self.proto_file = proto_file
        self.client_file = client_file
        self.client_type_call = "qa_client" if client_type == ClientType.QA else "client"

    def generate_code(self):
        """generate a python code string and write it to the given file"""
        self._generate_code(
            in_file=self.in_file,
            out_file=self.out_file,
            proto_file=self.proto_file,
            client_file=self.client_file,
        )

    @staticmethod
    def read_file_lines(in_file: str) -> List[str]:
        """open file and read lines into list"""
        with open(in_file, "r") as f:
            lines = f.readlines()
        return lines

    @staticmethod
    def write_to_python_file(out_file: str, generated_code: str):
        """write list to file"""
        with open(out_file, "wt") as f:
            f.write(generated_code)

    @staticmethod
    def get_filenames(in_file: str) -> Tuple[str, str, str]:
        """parse import paths and filenames from the </path/to/xxxx_pb2.py> input file"""
        grpc_filename = in_file.split("/")[-1].replace(".py", "")
        pb2_filename = grpc_filename.replace("_grpc", "")
        part_of_path = in_file.split("ondewo/")[1].split(grpc_filename)[0].replace("/", ".")
        import_path = f"ondewo.{part_of_path}"[:-1]
        return import_path, grpc_filename, pb2_filename

    @staticmethod
    def find_class_in_python_file(lines: List[str], end_of_class_string: str = "Servicer(object)") -> List[str]:
        """
        find the class with <end_of_class_string> in its definition and return its code lines
        """

        # find relevant class in code
        class_start_idx = 0
        for i, line in enumerate(lines):
            if end_of_class_string in line:
                class_start_idx = i
                break
        class_end_idx = len(lines) - 1
        for i in range(class_start_idx + 1, len(lines)):
            tab_length_in_spaces = 4
            line = lines[i]
            if line == "\n":
                continue
            elif (
                    line[:tab_length_in_spaces] != "    "
                    or "def" in line[:tab_length_in_spaces]
                    or "class" in line[:tab_length_in_spaces]
            ):
                class_end_idx = i - 1
                break

        # generate list with relevant base code, and a copy for code auto-generation
        class_lines = lines[class_start_idx:class_end_idx + 1]
        return class_lines

    def get_class_info_from_lines(self, lines: List[str]) -> Tuple[str, str, List[str]]:
        """
        extract information on the first class defined in a python file
        returns the class name, base class name and docstring
        """
        for i, line in enumerate(lines):
            if "class" in line:
                if "(" in line:
                    class_name = line.split("class ")[1].split("(")[0]
                    base_name = line.split("(")[1].split(")")[0]
                else:
                    class_name = line.split("class ")[1].split(":")[0]
                    base_name = ""

                docstring_lines = self.get_docstring_lines(start_idx=i + 1, lines=lines)

                return class_name, base_name, docstring_lines

        # raise Error if no class was found
        raise ValueError("no 'class' found in code lines!")

    @staticmethod
    def get_docstring_lines(start_idx: int, lines: List[str]) -> List[str]:
        """
        parse the docstring from code lines
        """

        # find docstring
        start_not_found = True
        docstring_start_idx = start_idx
        docstring_end_idx = start_idx
        for j in range(start_idx, len(lines)):
            if '"""' in lines[j] and start_not_found:
                docstring_start_idx = j
                start_not_found = False
                if len(lines[j].split('"""')) > 2:
                    docstring_end_idx = j
                    break
            if '"""' in lines[j] and not start_not_found:
                docstring_end_idx = j
                break

        # get docstring lines
        docstring_lines = []
        for j in range(docstring_start_idx, docstring_end_idx + 1):
            if j == docstring_start_idx:
                docstring = lines[j].split('"""')[1]
            else:
                docstring = lines[j].split('"""')[0]
            docstring_lines.append(docstring)

        return docstring_lines

    def get_function_info_from_lines(self, lines: List[str]) -> Dict[str, Tuple[List[str], List[str]]]:
        """
        extract information on functions defined in python file by parsing code lines
        will return a dictionary with function_name -> (function_arguments, function_docstring)
        """
        functions_info = {}
        for i, line in enumerate(lines):
            if "def " in line:
                kk = i
                while ")" not in line and kk < len(lines):  # multi-line def statement support
                    kk += 1
                    line += lines[kk]
                    line = line.replace("\n", "")
                function_name = line.split("def ")[1].split("(")[0]
                args = line.split("(")[1].split(")")[0].replace(" ", "").replace("\n", "").split(",")
                docstring_lines = self.get_docstring_lines(start_idx=kk + 1, lines=lines)
                functions_info[function_name] = (args, docstring_lines)

        return functions_info

    def get_function_info_from_proto(self, proto_file: str) -> Dict[str, Tuple[str, str, Optional[str], Optional[str]]]:
        """
        get endpoint information from proto file
        extracts lines with 'rpc' and reads the endpoint name + request and response messages
        returns a dictionary with: endpoint_name -> (request, response) [messages]
        """
        lines = self.read_file_lines(proto_file)

        # get rpc definition lines with request/response message information
        rpc_lines = []
        for line in lines:
            if re.findall("^\s*rpc", line):
                rpc_lines.append(line)

        # parse request/response messages for rpc endpoint from rpc definition lines
        # assuming: rpc SomeEndpoint (SomeRequest) returns (SomeResponse)
        # stream requests/responses also supported
        endpoint_info = {}
        for line in rpc_lines:
            endpoint = line.split("rpc ")[1].split(" (")[0]
            request = line.split(f"{endpoint} (")[1].split(") returns")[0]
            request_type = "stream" if "stream" in request else None
            request = request.replace("stream ", "")

            response = line.split("returns (")[1].split(")")[0]
            response_type = "stream" if "stream" in response else None
            response = response.replace("stream ", "")

            if "protobuf.Empty" in request:
                request = "Empty"
            if "protobuf.Empty" in response:
                response = "Empty"
            if "Operation" in response:
                response = "Operation"
            endpoint_info[endpoint] = (request, response, request_type, response_type)

        return endpoint_info

    def get_client_service_function_name(self, client_file: str) -> Dict[str, Tuple[str, str]]:
        """
        get all functions and their requests/responses from the client file
        """
        lines = self.read_file_lines(client_file)
        client_info = {}
        for k, line in enumerate(lines):
            if "def " in line:
                kk = k
                while ")" not in line and kk < len(lines):  # multi-line def statements
                    kk += 1
                    line += lines[kk]
                function_name = line.split("def ")[1].split("(")[0]
                if "request" in line:
                    request = (
                        line.split(": ")[1].split(")")[0].replace("stream ", "").replace("\n", "").replace(" ", "")
                    )
                else:
                    request = "Empty"
                if "->" in line:
                    response = (
                        line.split("->")[1].split(":")[0].replace("stream ", "").replace("\n", "").replace(" ", "")
                    )
                    if "Operation" in response:
                        response = "Operation"
                    if "Empty" in request:
                        request = "Empty"
                    if "Empty" in response:
                        response = "Empty"
                else:
                    response = "Empty"
                client_info[function_name] = (request, response)
        return client_info

    @staticmethod
    def get_client_service_name(client_file: str) -> str:
        return client_file.split("/")[-1].replace(".py", "")

    @staticmethod
    def try_convert_function_name(function_name: str) -> str:
        """converters CamelCase to camel_case"""
        new_function_name = ""
        for i, letter in enumerate(function_name):
            if letter.isupper():
                if i == 0:
                    new_function_name += letter.lower()
                else:
                    new_function_name += "_" + letter.lower()
            else:
                new_function_name += letter
        return new_function_name

    def build_functions_coder_objects(
            self,
            indent_lvl: int,
            function_info: Dict[str, Tuple[List[str], List[str]]],
            pb2_filename: str,
            endpoint_info: Dict[str, Tuple[str, str, Optional[str], Optional[str]]],
            client_info: Dict[str, Tuple[str, str]],
            client_service_name: str,
    ) -> Tuple[List[FunctionCoder], List[bool]]:
        functions = []

        include_google_import, include_empty_import, include_operation_import, include_typing_import = (False, False, False, False)
        for function_name, (request, response, request_type, response_type ) in endpoint_info.items():

            # try to find corresponding client function by request/response types
            client_function_name = "[NOT_FOUND]"
            for some_client_function_name, (search_request, search_response) in client_info.items():
                if (request, response) == (
                        search_request.replace(pb2_filename + ".", ""),
                        search_response.replace(pb2_filename + ".", ""),
                ):
                    client_function_name = some_client_function_name
                    break

            # if not found, try to construct it from convention, or skip export of this endpoint
            if client_function_name == "[NOT_FOUND]":
                converted_function_name = self.try_convert_function_name(function_name=function_name)
                if converted_function_name in client_info.keys():
                    client_function_name = converted_function_name
                    (request, response) = client_info[converted_function_name]
                else:
                    if "Empty" in request and "Empty" in response:
                        print(
                            f"BOTH REQUEST AND RESPONSE EMPTY FOR > {client_service_name} < ENDPOINT: "
                            + f"{function_name}(); CANNOT ASSIGN CLIENT FUNCTION; --> SKIPPED"
                        )
                    else:
                        print(
                            f"COULD NOT FIND CLIENT FUNCTION FOR > {client_service_name} < ENDPOINT: "
                            + f"{function_name}() --> SKIPPED"
                        )
                    continue

            # handle function meta information (typing, returns, handle empty requests)

            # request types and imports
            args, docstring = function_info[function_name]
            set_fct_input_empty = False
            arg_dict = {}
            type_dict = {"self": "", }
            request_str = "request"
            for arg in args:
                if arg == "request":
                    request_str = "request"
                    if "Empty" in request:
                        type_dict[arg] = f"{request}"
                        include_empty_import = True
                        set_fct_input_empty = True
                    else:
                        type_dict[arg] = f"{pb2_filename}.{request}"
                if arg == "request_iterator":
                    request = re.findall("\[(.*)\]",request)
                    type_dict[arg] = (f"Iterator[{pb2_filename}.{request[0]}]")
                    request_str = "request_iterator"
                if arg == "context":
                    type_dict[arg] = "grpc.ServicerContext"
                arg_dict[arg] = type_dict[arg]

            # response types and imports
            if response != "":
                if "Empty" in response or "google" in response or "Operation" in response:
                    if "google" in response:
                        include_google_import = True
                    if "Empty" in response:
                        include_empty_import = True
                    if "Operation" in response:
                        include_operation_import = True
                    returns = {"response": f"{response}"}
                else:
                    if "Iterator" in response:
                        include_typing_import = True
                        response = re.findall("\[(.*)\]", response)
                        response = f"Iterator[{pb2_filename}.{response[0]}]"
                        returns = {"response": response}
                    else:
                        returns = {"response": f"{pb2_filename}.{response}"}
            else:
                returns = {}

            # nlu-client service function input -> client.services.something(<input>=<input>)
            if set_fct_input_empty:
                fc_input = ""
            else:
                fc_input = f"{request_str}={request_str}"
            docstring = ["[AUTO-GENERATED FUNCTION]"] + docstring

            # create Function object, which can generate the python code and append it to a list
            f = FunctionCoder(
                function_name=function_name,
                indent_lvl=indent_lvl,
                arguments=arg_dict,
                add_lines=[
                    f'logger.info("relaying {function_name}() to nlu-client...")',
                    f"response = self.{self.client_type_call}.services.{client_service_name}.{client_function_name}({fc_input})",
                ],
                returns=returns,
                docstring=docstring,
            )
            functions.append(f)
        bools = [include_google_import, include_empty_import, include_operation_import, include_typing_import]
        return functions, bools

    @staticmethod
    def clean_up_code(generated_code: str) -> str:
        # split into code lines
        lines = generated_code.split("\n")

        # fix line-by-line
        for i, line in enumerate(lines):

            # remove spaces in empty lines
            if len(line.replace(" ", "")) == 0:
                lines[i] = ""
                line = lines[i]

            if len(line) >= 1:
                # remove spaces at end of line
                while line[-1] == " ":
                    lines[i] = lines[i][:-1]
                    line = lines[i]

        # re-assemble code string and return
        generated_code = ""
        for line in lines:
            generated_code += line + "\n"

        # add a comment at the end of the file to fix flake8 error (removing the last newline still has it complaining)
        generated_code += "# [make flake8 shut up]\n"
        return generated_code

    def _generate_code(
            self,
            in_file: str,
            out_file: str,
            proto_file: str,
            client_file: str,
    ) -> None:

        # parse information from files
        print(f'Generating code for proto file: {proto_file}')
        lines = self.read_file_lines(in_file=in_file)
        class_lines = self.find_class_in_python_file(lines=lines)
        class_info = self.get_class_info_from_lines(lines=class_lines)
        import_path, grpc_filename, pb2_filename = self.get_filenames(in_file=in_file)
        function_info = self.get_function_info_from_lines(lines=class_lines)
        endpoint_info = self.get_function_info_from_proto(proto_file=proto_file)
        client_info = self.get_client_service_function_name(client_file=client_file)
        client_service_name = self.get_client_service_name(client_file=client_file)

        #################
        # generate code
        #################

        # get endpoint function code
        base_indent = 0
        functions, (include_google_import, include_empty_import, include_operation_import, include_typing_import) = \
            self.build_functions_coder_objects(
                indent_lvl=base_indent + 1,
                function_info=function_info,
                pb2_filename=pb2_filename,
                endpoint_info=endpoint_info,
                client_info=client_info,
                client_service_name=client_service_name,
            )

        # create header
        header = (
                "# Copyright 2021 ONDEWO GmbH\n" +
                "#\n" +
                "# Licensed under the Apache License, Version 2.0 (the \"License\");\n" +
                "# you may not use this file except in compliance with the License.\n" +
                "# You may obtain a copy of the License at\n" +
                "#\n" +
                "#     http://www.apache.org/licenses/LICENSE-2.0\n" +
                "#\n" +
                "# Unless required by applicable law or agreed to in writing, software\n" +
                "# distributed under the License is distributed on an \"AS IS\" BASIS,\n" +
                "# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n" +
                "# See the License for the specific language governing permissions and\n" +
                "# limitations under the License.\n" +
                "#\n" +
                "# [AUTO-GENERATED FILE]\n\n"
        )

        # create imports
        google_import, empty_import, operation_import, typing_import = ("", "", "","")
        if include_google_import:
            google_import = "import google\n"
        if include_typing_import:
            typing_import = "from typing import Iterator\n\n"
        if include_empty_import:
            empty_import = "from google.protobuf.empty_pb2 import Empty\n"
        if include_operation_import:
            operation_import = "from google.longrunning.operations_grpc_pb2 import Operation\n"
        imports = (
                "from abc import ABCMeta, abstractmethod\n"
                + "\n"
                + f"{typing_import}"
                + f"{google_import}"
                + "import grpc\n"
                + f"{operation_import}"
                + f"{empty_import}"
                + f"from {import_path} import {pb2_filename}\n"
                + f"from {import_path}.client import Client\n"
                + f"from {import_path}.{grpc_filename} import {class_info[0]}\n"
                + "from ondewo.logging.logger import logger\n"
                + "\n"
                + "\n"
        )

        # create class docstring
        class_docstring = class_info[2]
        script_name = __file__.split("/")[-1]
        class_docstring = [
            "[AUTO-GENERATED CLASS]",
            f"generated by: {script_name}",
            "DO NOT ALTER CODE UNLESS YOU WANT TO DO IT EVERY TIME YOU GENERATE IT!",
            "",
            "used to relay endpoints to the functions defined in: ",
            f"  >> {client_file}",
            "any child class is expected to have a .client attribute to send the service calls to (metaclass-enforced)",
            "all function/endpoint calls are logged",
            "override functions if other functionality than a client call is needed",
            "",
            "[original docstring]",
            *class_docstring,
        ]

        # create endpoint class initial code (__init__/__metaclass__/etc.)
        inits = [
            "__metaclass__ = ABCMeta",
            "",
            "@property",
            "@abstractmethod",
            f"def {self.client_type_call}(self) -> Client:",
            "    pass",
        ]

        # create Class object and generate code string
        coder_class = ClassCoder(
            name="Auto" + class_info[0],
            base_class=class_info[0],
            docstring=class_docstring,
            inits=inits,
            indent_lvl=base_indent,
            functions=functions,
        )
        generated_code = header + imports + coder_class.get_code_string()
        generated_code = self.clean_up_code(generated_code)

        # write to file
        self.write_to_python_file(out_file=out_file, generated_code=generated_code)
