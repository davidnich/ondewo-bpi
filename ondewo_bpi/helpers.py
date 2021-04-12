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

from typing import Any, Dict, Optional, List

from grpc._channel import _InactiveRpcError
from ondewo.nlu import context_pb2, session_pb2
from ondewo.nlu.client import Client
from ondewo.logging.logger import logger_console


def add_params_to_cai_context(
    client: Client,
    response: session_pb2.DetectIntentResponse,
    params: Dict[str, Any],
    context: str,
) -> None:
    _add_params_to_cai_context(
        client=client,
        session=get_session_from_response(response),
        params=params,
        context=context,
    )


def _add_params_to_cai_context(
    client: Client,
    session: str,
    params: Dict[str, Any],
    context: str,
) -> None:
    logger_console.info(
        {
            "message": "adding parameter to cai",
            "paramter": params,
            "context": context,
            "tags": ["parameters", "contexts"],
        }
    )
    parameters = create_parameter_dict(params)
    try:
        request = context_pb2.GetContextRequest(name=f"{session}/contexts/{context}")
        existing_context = client.services.contexts.get_context(request)
        for k, v in parameters.items():
            existing_context.parameters[k].CopyFrom(v)
        client.services.contexts.update_context(
            request=context_pb2.UpdateContextRequest(
                context=existing_context
            )
        )
    except _InactiveRpcError:
        context = context_pb2.Context(
            name=f"{session}/contexts/{context}",
            lifespan_count=100,
            parameters=parameters,
            lifespan_time=1000
        )
        client.services.contexts.create_context(
            request=context_pb2.CreateContextRequest(
                parent=f'{session}',
                context=context,
            )
        )


def delete_param_from_cai_context(
    client: Client,
    response: session_pb2.DetectIntentResponse,
    param_name: str,
    context: str
) -> None:
    logger_console.info(
        {
            "message": "deleting parameter from cai",
            "paramter": param_name,
            "context": context,
            "tags": ["parameters", "contexts"],
        }
    )
    session = get_session_from_response(response)
    context_name = f"{session}/contexts/{context}"
    existing_context = client.services.contexts.get_context(request=context_pb2.GetContextRequest(name=context_name))
    try:
        del existing_context.parameters[param_name]
        client.services.contexts.delete_context(request=context_pb2.DeleteContextRequest(name=context_name))
        client.services.contexts.create_context(
            request=context_pb2.CreateContextRequest(parent=session, context=existing_context)
        )
    except KeyError:
        logger_console.exception(
            {
                "message": "tried to delete param that didnt exist",
                "parameter": param_name,
                "context": context,
                "tags": ["parameters", "contexts"],
            }
        )


def detect_intent(
    client: Client,
    response: session_pb2.DetectIntentResponse,
    text: str
) -> session_pb2.DetectIntentResponse:
    logger_console.info({"message": "detect intent triggered in bpi helpers", "tags": ["timing"]})
    request = get_detect_intent_request(text=text, session=get_session_from_response(response=response),)
    logger_console.info({"message": "detect intent returned in bpi helpers", "tags": ["timing"]})
    result = client.services.sessions.detect_intent(request)
    logger_console.warning(f"wrote {text}, received {result.query_result.fulfillment_messages}")
    return result


def get_detect_intent_request(
    session: str,
    text: str,
    language: str = 'de-DE',
    query_params: Optional[session_pb2.QueryParameters] = None
) -> session_pb2.DetectIntentRequest:
    request = session_pb2.DetectIntentRequest(
        session=session,
        query_input=session_pb2.QueryInput(text=session_pb2.TextInput(text=text, language_code=language),),
        query_params=query_params,
    )
    return request


def create_parameter_dict(my_dict: Dict) -> Optional[Dict[str, context_pb2.Context.Parameter]]:
    assert isinstance(my_dict, dict) or my_dict is None, "parameter must be a dict or None"
    if my_dict is not None:
        return {
            key: context_pb2.Context.Parameter(
                display_name=key,
                value=my_dict[key]
            )
            for key in my_dict
        }
    return None


# This function creates a detect intent request that will trigger a specific intent
#   using the 'exact intent' trigger
def trigger_intent(
    client: Client,
    session: str,
    intent_name: str,
    language: str = "de-DE",
    additional_contexts: Optional[List[context_pb2.Context]] = None,
) -> session_pb2.DetectIntentResponse:
    """
    Trigger a specific intent in the NLU backend without intent matching.

    Args:
        client: nlu client
        session: full session to perform the trigger in ('parent/<PROJECT_ID>/agent/sessions/<SESSION_ID>')
        intent_name: intent that you want to trigger
        language: language of the project
        additional_contexts: if you want to add additional contexts to the session

    Returns:
        session_pb2.DetectIntentResponse
    """
    if not additional_contexts:
        additional_contexts = []

    logger_console.warning({"message": "triggering specific intent", "intent_name": intent_name})
    trigger_context = create_context_struct(
        context=f"{session}/contexts/exact_intent",
        parameters=create_parameter_dict({"intent_name": intent_name}),
        lifespan_count=1,
    )
    request = get_detect_intent_request(
        text=f"Triggering Specific Intent: {intent_name}",
        session=session,
        language=language,
        query_params=session_pb2.QueryParameters(contexts=[trigger_context, *additional_contexts]),
    )
    result = client.services.sessions.detect_intent(request)
    logger_console.warning(f"triggered {intent_name}")
    return result


def create_context_struct(context: str, parameters: Optional[Dict[str, context_pb2.Context.Parameter]], lifespan_count: int = 5) -> context_pb2.Context:
    context_struct: context_pb2.Context = context_pb2.Context(
        name=f"{context}", lifespan_count=lifespan_count, parameters=parameters
    )
    return context_struct


# This function deletes periods from the text in a request
def strip_final_periods_from_request(request: session_pb2.DetectIntentRequest,) -> session_pb2.DetectIntentRequest:
    stripped = request.query_input.text.text.strip(".")
    request.query_input.text.text = stripped
    return request


def get_session_from_response(response: session_pb2.DetectIntentResponse) -> str:
    return response.query_result.diagnostic_info["sessionId"]   # type: ignore
