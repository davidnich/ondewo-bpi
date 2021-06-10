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

import datetime
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from google.protobuf.json_format import MessageToJson
from ondewo.nlu import context_pb2, intent_pb2, session_pb2
from ondewo.logging.logger import logger_console

from ondewo_bpi.constants import DATE_FORMAT, DATE_FORMAT_BACK, EnglishDays, GermanDays, QueryTriggers, SipTriggers


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


class MessageHandler:
    """
    This class takes a grpc response and decomposes the message into multiple parts, processes them asynchronously and
    sends the reponses to all available enpoints. Once the processing is complete, the message is reassembled and sent
    back.

    The subclasser should implment 'quicksend_to_api' if they want messages to be send to an endpoint out of turn (aka
    before the whole response is finished), and should implement functions for each of the triggers that they want to
    handle and update self.trigger_function_map with the new functions.
    """

    @staticmethod
    def get_triggers(message: intent_pb2.Intent.Message, session_id: Optional[str] = None) -> Dict[str, List[str]]:
        found_triggers: Dict[str, List[str]] = {}
        for trigger in SipTriggers:
            if SingleMessageHandler.check_message_for_pattern(message, trigger.value):
                content = SingleMessageHandler.get_pattern_from_message(message, trigger.value)
                found_triggers[trigger.value] = content
        for qtrigger in QueryTriggers:
            if SingleMessageHandler.check_message_for_pattern(message, qtrigger.value):
                content = SingleMessageHandler.get_pattern_from_message(message, qtrigger.value)
                found_triggers[qtrigger.value] = content
        if len(found_triggers):
            logger_console.info({"message": f"Found triggers: {found_triggers}", "found_triggers": found_triggers, "session_id": session_id})
        return found_triggers

    @staticmethod
    def check_for_pattern(pattern: str, response: session_pb2.DetectIntentResponse,) -> bool:
        for message in response.query_result.fulfillment_messages:
            if not len(message.text.text):
                continue
            if SingleMessageHandler.check_message_for_pattern(message, pattern):
                return True
        return False

    @staticmethod
    def substitute_pattern(
        pattern: str, replace: str, response: session_pb2.DetectIntentResponse,
    ) -> session_pb2.DetectIntentResponse:
        logger_console.info({"message": "replacing text in response", "pattern": pattern, "replace": replace})
        for j, message in enumerate(response.query_result.fulfillment_messages):
            SingleMessageHandler.substitute_pattern_in_message(message, pattern, replace)
        return response

    @staticmethod
    def reformat_date(response: session_pb2.DetectIntentResponse,) -> session_pb2.DetectIntentResponse:
        logger_console.info("reformatting date in response")
        for message in response.query_result.fulfillment_messages:
            if not len(message.text.text):
                continue
            SingleMessageHandler.reformat_date_in_message(message)
        return response

    @staticmethod
    def strip_seconds(response: session_pb2.DetectIntentResponse,) -> session_pb2.DetectIntentResponse:
        logger_console.info("strip seconds from text in response")
        for message in response.query_result.fulfillment_messages:
            if not len(message.text.text):
                continue
            SingleMessageHandler.strip_seconds_in_message(message)
        return response

    @staticmethod
    def add_weekday(response: session_pb2.DetectIntentResponse, days: Union[EnglishDays, GermanDays] = GermanDays) -> session_pb2.DetectIntentResponse:
        logger_console.info("add weekday to date in response")
        for message in response.query_result.fulfillment_messages:
            if not len(message.text.text):
                continue
            SingleMessageHandler.add_weekday_in_message(message, days)
        return response

    @staticmethod
    def check_for_triggers(response: session_pb2.DetectIntentResponse,) -> Tuple[List[str], List[str]]:
        found_triggers: List[str] = []
        trigger_content: List[str] = []
        for j, message in enumerate(response.query_result.fulfillment_messages):
            if not len(message.text.text):
                continue
            for trigger in SipTriggers:
                if SingleMessageHandler.check_message_for_pattern(message, trigger.value):
                    found_triggers.append(trigger.value)
                    trigger_content.extend(SingleMessageHandler.get_pattern_from_message(message, trigger.value))
        return found_triggers, trigger_content  # type: ignore

    @staticmethod
    def remove_triggers_from_reponse(response: session_pb2.DetectIntentResponse,) -> session_pb2.DetectIntentResponse:
        for j, message in enumerate(response.query_result.fulfillment_messages):
            if not len(message.text.text):
                continue
            for trigger in SipTriggers:
                SingleMessageHandler.substitute_pattern_in_message(message, trigger.value, "")
        return response


class ParameterMethods:
    @staticmethod
    def get_context(response: session_pb2.DetectIntentResponse, context_name: str) -> Optional[context_pb2.Context]:
        logger_console.info({"message": "searching for context", "content": context_name, "tags": ["contexts"]})
        context = [c for c in response.query_result.output_contexts if c.name == context_name]
        logger_console.info(
            {"message": "found context", "content": MessageToJson(context[0]) if len(context) else "None"}
        )
        return context[0] if len(context) else None

    @staticmethod
    def get_param(response: session_pb2.DetectIntentResponse, param_name: str, context_name: str,) -> Any:
        logger_console.info({"message": "getting param", "content": context_name, "tags": ["parameters"]})
        context = ParameterMethods.get_context(response=response, context_name=context_name)
        if context is None:
            return None

        params = list(context.parameters)
        if param_name in params:
            returned_param = context.parameters[param_name]
        else:
            returned_param = "None"

        try:
            returned_param = MessageToJson(returned_param)
        except AttributeError:
            pass

        logger_console.info({"message": "found param", "content": returned_param})
        return context.parameters[param_name] if param_name in params else None

    @staticmethod
    def add_params_to_response(
        response: session_pb2.DetectIntentResponse, params: Dict[str, Any], context_name: str,
    ) -> session_pb2.DetectIntentResponse:
        logger_console.info(
            {
                "message": "adding parameter to response",
                "paramter": params,
                "context": context_name,
                "tags": ["parameters", "contexts"],
            }
        )
        parameters = create_parameter_dict(params)
        for j, i in enumerate(response.query_result.output_contexts):
            if i.name == context_name:
                for k, v in parameters.items():
                    i.parameters[k].CopyFrom(v)
        return response

    @staticmethod
    def delete_param_from_response(response: session_pb2.DetectIntentResponse, param_name: str) -> None:
        logger_console.info(
            {"message": "deleting parameter from response", "parameter": param_name, "tags": ["parameters"]}
        )
        for context in response.query_result.output_contexts:
            if param_name in context.parameters:
                del context.parameters[param_name]


class SingleMessageHandler:
    @staticmethod
    def check_message_for_pattern(message: intent_pb2.Intent.Message, pattern: str) -> bool:
        logger_console.debug({"message": "checking response for text", "content": pattern, "pattern": pattern})
        if message.HasField("text"):
            has_match = SingleMessageHandler._pattern_match_text(message, pattern)
            if has_match:
                return has_match
        if message.HasField("card"):
            has_match = SingleMessageHandler._pattern_match_card(message, pattern)
            if has_match:
                return has_match
        return False

    @staticmethod
    def _pattern_match_text(message: intent_pb2.Intent.Message, pattern: str) -> bool:
        return not not re.findall(pattern, "".join(message.text.text),)

    @staticmethod
    def _pattern_match_card(message: intent_pb2.Intent.Message, pattern: str) -> bool:
        return not not re.findall(pattern, "".join(message.card.subtitle),)

    # TODO: this needs to be improved for more general cases
    @staticmethod
    def get_pattern_from_message(message: intent_pb2.Intent.Message, pattern: str) -> List[str]:
        content: List[str] = []
        if message.HasField("text"):
            content.extend(SingleMessageHandler._get_pattern_from_message_text(message, pattern))
        if message.HasField("card"):
            content.extend(SingleMessageHandler._get_pattern_from_message_card(message, pattern))
        return content

    @staticmethod
    def _get_pattern_from_message_text(message: intent_pb2.Intent.Message, pattern: str) -> List[str]:
        match = re.findall(pattern, message.text.text[0])
        return [i.strip("(").strip(")").strip("'") for i in match]

    @staticmethod
    def _get_pattern_from_message_card(message: intent_pb2.Intent.Message, pattern: str) -> List[str]:
        match = re.findall(pattern, message.card.subtitle)
        return [i.strip("(").strip(")").strip("'") for i in match]

    @staticmethod
    def substitute_pattern_in_message(
        message: intent_pb2.Intent.Message, pattern: str, replace: str, once: bool = False
    ) -> intent_pb2.Intent.Message:
        if message.HasField("text"):
            message = SingleMessageHandler._text_substitution_text(message, pattern, replace, once)
        if message.HasField("card"):
            message = SingleMessageHandler._text_substitution_card(message, pattern, replace, once)
        return message

    @staticmethod
    def _text_substitution_text(
        message: intent_pb2.Intent.Message, pattern: str, replace: str, once: bool
    ) -> intent_pb2.Intent.Message:
        if not len(message.text.text):
            return message
        match: Union[bool, re.Match] = True  # type: ignore
        while match:
            match = re.match(f"(.*)({pattern})(.*)", message.text.text[0])  # type: ignore
            if match:
                new_response = "".join([match.groups()[0], replace, match.groups()[-1]])  # type: ignore
                message.text.text[0] = new_response
                if once:
                    break
        return message

    @staticmethod
    def _text_substitution_card(
        message: intent_pb2.Intent.Message, pattern: str, replace: str, once: bool
    ) -> intent_pb2.Intent.Message:
        match: Union[bool, re.Match] = True  # type: ignore
        while match:
            match = re.match(f"(.*)({pattern})(.*)", message.card.subtitle)  # type: ignore
            if match:
                new_response = "".join([match.groups()[0], replace, match.groups()[-1]])  # type: ignore
                message.card.subtitle = new_response
                if once:
                    break
        return message

    @staticmethod
    def reformat_date_in_message(message: intent_pb2.Intent.Message) -> intent_pb2.Intent.Message:
        if message.HasField("text"):
            message = SingleMessageHandler._reformat_date_text(message)
        if message.HasField("card"):
            message = SingleMessageHandler._reformat_date_card(message)
        return message

    @staticmethod
    def _reformat_date_card(message: intent_pb2.Intent.Message) -> intent_pb2.Intent.Message:
        match: Union[bool, re.Match] = True  # type: ignore
        while match:
            match = re.match(r"(.*)(\d{4}.*T\d\d:\d\d:\d\d)(.*)", message.card.subtitle)  # type: ignore
            if match:
                date = datetime.datetime.fromisoformat(match.groups()[1])  # type: ignore
                new_response = "".join(
                    [match.groups()[0], date.strftime(DATE_FORMAT), match.groups()[2]]  # type: ignore
                )
                message.card.subtitle = new_response
                logger_console.info(f"DATE: {date} formatted to DATE: {date.strftime(DATE_FORMAT)}")
        return message

    @staticmethod
    def _reformat_date_text(message: intent_pb2.Intent.Message) -> intent_pb2.Intent.Message:
        match: Union[bool, re.Match] = True  # type: ignore
        while match:
            match = re.match(r"(.*)(\d{4}.*T\d\d:\d\d:\d\d)(.*)", message.text.text[0])  # type: ignore
            if match:
                date = datetime.datetime.fromisoformat(match.groups()[1])  # type: ignore
                new_response = "".join(
                    [match.groups()[0], date.strftime(DATE_FORMAT), match.groups()[2]]  # type: ignore
                )
                message.text.text[0] = new_response
                logger_console.info(f"DATE: {date} formatted to DATE: {date.strftime(DATE_FORMAT)}")
        return message

    @staticmethod
    def strip_seconds_in_message(message: intent_pb2.Intent.Message) -> intent_pb2.Intent.Message:
        if message.HasField("text"):
            message = SingleMessageHandler._strip_seconds_text(message)
        if message.HasField("card"):
            message = SingleMessageHandler._strip_seconds_card(message)
        return message

    @staticmethod
    def _strip_seconds_card(message: intent_pb2.Intent.Message) -> intent_pb2.Intent.Message:
        match: Union[bool, re.Match] = True  # type: ignore
        while match:
            match = re.match(r"(.*)(\d\d:\d\d:\d\d)(.*)", message.card.subtitle)  # type: ignore
            if match:
                time = match.groups()[1]
                new_response = "".join(
                    [match.groups()[0], time[:-3], match.groups()[2]]  # type: ignore
                )
                message.card.subtitle = new_response
                logger_console.info(f"DATE: {time} formatted to DATE: {time[:-2]}")
        return message

    @staticmethod
    def _strip_seconds_text(message: intent_pb2.Intent.Message) -> intent_pb2.Intent.Message:
        match: Union[bool, re.Match] = True  # type: ignore
        while match:
            match = re.match(r"(.*)(\d\d:\d\d:\d\d)(.*)", message.text.text[0])  # type: ignore
            if match:
                time = match.groups()[1]
                new_response = "".join(
                    [match.groups()[0], time[:-3], match.groups()[2]]  # type: ignore
                )
                message.text.text[0] = new_response
                logger_console.info(f"DATE: {time} formatted to DATE: {time[:-2]}")
        return message

    @staticmethod
    def add_weekday_in_message(message: intent_pb2.Intent.Message, days: Union[EnglishDays, GermanDays]) -> intent_pb2.Intent.Message:
        if message.HasField("text"):
            message = SingleMessageHandler._add_weekday_text(message, days)
        if message.HasField("card"):
            message = SingleMessageHandler._add_weekday_card(message, days)
        return message

    @staticmethod
    def _add_weekday_card(message: intent_pb2.Intent.Message, days: Union[EnglishDays, GermanDays]) -> intent_pb2.Intent.Message:
        date_regex = r"\d\d\D\d\d\D\d\d\d\d"
        matches = len(re.findall(date_regex, message.card.subtitle))
        if matches > 1:
            print("Multiple date subtitutions on one line! Not supported. Will only substitute the first")
        match = re.match(rf"(.*)({date_regex})(.*)", message.card.subtitle)  # type: ignore
        if match:
            time = match.groups()[1]
            day_of_the_week_index = int(datetime.datetime.strptime(time, DATE_FORMAT_BACK).strftime("%w"))
            day = list(iter(days))[day_of_the_week_index].value
            new_response = "".join(
                [match.groups()[0], day, time, match.groups()[2]]  # type: ignore
            )
            message.card.subtitle = new_response
            logger_console.info(f"DATE: {time} formatted to DATE: {time[:-2]}")
        return message

    @staticmethod
    def _add_weekday_text(message: intent_pb2.Intent.Message, days: Union[EnglishDays, GermanDays]) -> intent_pb2.Intent.Message:
        date_regex = r"\d\d\D\d\d\D\d\d\d\d"
        matches = len(re.findall(date_regex, message.text.text[0]))
        if matches > 1:
            print("Multiple date subtitutions on one line! Not supported. Will only substitute the first")
        match = re.match(fr"(.*)({date_regex})(.*)", message.text.text[0])  # type: ignore
        if match:
            time = match.groups()[1]
            day_of_the_week_index = int(datetime.datetime.strptime(time, DATE_FORMAT_BACK).strftime("%w"))
            day = list(iter(days))[day_of_the_week_index].value
            new_response = "".join(
                [match.groups()[0], day, time, match.groups()[2]]  # type: ignore
            )
            message.text.text[0] = new_response
            logger_console.info(f"DATE: {time} formatted to DATE: {time[:-2]}")
        return message
