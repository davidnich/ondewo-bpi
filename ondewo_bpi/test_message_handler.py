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
from contextlib import nullcontext as does_not_raise
from typing import Any, Dict, List

import pytest
from ondewo.nlu import intent_pb2, session_pb2

import ondewo_bpi.config as file_anchor  # noqa: F401
from ondewo_bpi.bpi_server import BpiServer
from ondewo_bpi.constants import DATE_FORMAT, QueryTriggers, SipTriggers, EnglishDays, GermanDays
from ondewo_bpi.message_handler import MessageHandler, SingleMessageHandler

REPLACEMENT_STRING = "replacement string"


def create_text_response(text: str) -> Any:
    return session_pb2.DetectIntentResponse(
        response_id="d07e62f1-e652-473c-b445-c77a0ad5260d",
        query_result=session_pb2.QueryResult(
            fulfillment_messages=[intent_pb2.Intent.Message(text=intent_pb2.Intent.Message.Text(text=[text]))]
        ),
    )


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        pytest.param("some random message", "some random message", marks=pytest.mark.xfail),
        (
            f"message with birthday: {datetime.datetime(1989, 4, 28).isoformat()}",
            f"message with birthday: {datetime.datetime(1989, 4, 28).strftime(DATE_FORMAT)}",
        ),
        (
            f"message with birthday: {datetime.datetime(1989, 4, 28, 22).isoformat()} in middle",
            f"message with birthday: {datetime.datetime(1989, 4, 28).strftime(DATE_FORMAT)} in middle",
        ),
        (
            f"message with multiple birthdays: {datetime.datetime(1989, 4, 28, 22).isoformat()} in {datetime.datetime(1989, 4, 20).isoformat()} middle",
            f"message with multiple birthdays: {datetime.datetime(1989, 4, 28).strftime(DATE_FORMAT)} in {datetime.datetime(1989, 4, 20).strftime(DATE_FORMAT)} middle",
        ),
    ],
)
def test_reformat_birthday_in_response(original_message, processed_message) -> None:
    response = create_text_response(original_message)
    response = MessageHandler.reformat_date(response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,expected_trigger",  # type: ignore
    [
        ("some random message", ([], [])),
        (
            f"message with trigger {SipTriggers.SIP_HANGUP.value}",
            ([SipTriggers.SIP_HANGUP.value], [SipTriggers.SIP_HANGUP.value],),
        ),
        (
            f"message with trigger {SipTriggers.SIP_HANGUP.value} in middle",
            ([SipTriggers.SIP_HANGUP.value], [SipTriggers.SIP_HANGUP.value],),
        ),
        (
            f"{SipTriggers.SIP_HANGUP.value} at start",
            ([SipTriggers.SIP_HANGUP.value], [SipTriggers.SIP_HANGUP.value],),
        ),
        (
            f"{SipTriggers.SIP_HUMAN_HANDOVER.value} at start",
            ([SipTriggers.SIP_HUMAN_HANDOVER.value], [SipTriggers.SIP_HUMAN_HANDOVER.value],),
        ),
        ("<SIP:SEND_NOW=('something')> at start", ([SipTriggers.SIP_SEND_NOW.value], ["something"]),),
        ("<SIP:PAUSE=('5s')> at start", ([SipTriggers.SIP_PAUSE.value], ["5s"])),
        (
            "<SIP:PAUSE=('5s')> at start <SIP:SEND_NOW=('something else')>",
            ([SipTriggers.SIP_SEND_NOW.value, SipTriggers.SIP_PAUSE.value], ["something else", "5s"],),
        ),
        (
            f"{SipTriggers.SIP_HUMAN_HANDOVER.value} triggers <SIP:SEND_NOW=('trigger1')> aplenty <SIP:SEND_NOW=('trigger2')> different kinds <SIP:PAUSE=('10s')>",
            (
                [SipTriggers.SIP_HUMAN_HANDOVER.value, SipTriggers.SIP_SEND_NOW.value, SipTriggers.SIP_PAUSE.value],
                [SipTriggers.SIP_HUMAN_HANDOVER.value, "trigger1", "trigger2", "10s"],
            ),
        ),
    ],
)
def test_check_response_for_triggers(original_message, expected_trigger) -> None:
    response = create_text_response(original_message)
    trigger = MessageHandler.check_for_triggers(response)
    assert trigger[0] == expected_trigger[0]
    assert trigger[1] == expected_trigger[1]


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("some random message", "some random message"),
        (f"message with trigger {SipTriggers.SIP_HANGUP.value}", "message with trigger ",),
        (f"message with trigger {SipTriggers.SIP_HANGUP.value} in middle", "message with trigger  in middle",),
        (f"message with trigger {SipTriggers.SIP_HANGUP.value}", "message with trigger ",),
        (f"{SipTriggers.SIP_HANGUP.value} at start", " at start"),
        (f"{SipTriggers.SIP_HUMAN_HANDOVER.value} at start", " at start"),
        ("<SIP:SEND_NOW=('something')> at start", " at start"),
        ("<SIP:PAUSE=('5s')> at start", " at start"),
        ("<SIP:PAUSE=('5s')> at start <SIP:SEND_NOW=('something else')>", " at start ",),
        (
            f"{SipTriggers.SIP_HUMAN_HANDOVER.value} triggers <SIP:SEND_NOW=('trigger1')> aplenty <SIP:SEND_NOW=('trigger2')> different kinds <SIP:PAUSE=('10s')>",
            " triggers  aplenty  different kinds ",
        ),
    ],
)
def test_remove_triggers_from_reponse(original_message, processed_message) -> None:
    response = create_text_response(original_message)
    response = MessageHandler.remove_triggers_from_reponse(response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,search,replace,processed_message",  # type: ignore
    [
        ("some random message", "random", "waldo", "some waldo message"),
        ("message with hash #hash.hash to change", "#hash.hash", "", "message with hash  to change",),
    ],
)
def test_replace_text_in_response(original_message, search, replace, processed_message) -> None:
    response = create_text_response(original_message)
    response = MessageHandler.substitute_pattern(search, replace, response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


class TestMessageHandler(BpiServer):
    def __init__(self) -> None:
        super().__init__()
        self.register_trigger_handler(SipTriggers.SIP_HANGUP.value, self.trigger_function_1)
        self.register_trigger_handler(SipTriggers.SIP_HUMAN_HANDOVER.value, self.trigger_function_2)
        self.register_trigger_handler(SipTriggers.SIP_SEND_NOW.value, self.replacement_function_self)
        self.register_trigger_handler(QueryTriggers.REPLACEMENT_TRIGGER.value, self.replacement_function_string)

    def trigger_function_1(
        self,
        response: session_pb2.DetectIntentResponse,
        message: intent_pb2.Intent.Message,
        trigger: str,
        found_triggers: Dict[str, List[str]],
    ) -> intent_pb2.Intent.Message:
        raise KeyError

    def trigger_function_2(
        self,
        response: session_pb2.DetectIntentResponse,
        message: intent_pb2.Intent.Message,
        trigger: str,
        found_triggers: Dict[str, List[str]],
    ) -> intent_pb2.Intent.Message:
        raise ValueError

    def replacement_function_self(
        self,
        response: session_pb2.DetectIntentResponse,
        message: intent_pb2.Intent.Message,
        trigger: str,
        found_triggers: Dict[str, List[str]],
    ) -> intent_pb2.Intent.Message:
        for content in found_triggers[trigger]:
            SingleMessageHandler.substitute_pattern_in_message(message, trigger, content, once=True)
        return message

    def replacement_function_string(
        self,
        response: session_pb2.DetectIntentResponse,
        message: intent_pb2.Intent.Message,
        trigger: str,
        found_triggers: Dict[str, List[str]],
    ) -> intent_pb2.Intent.Message:
        SingleMessageHandler.substitute_pattern_in_message(message, trigger, REPLACEMENT_STRING)
        return message


@pytest.mark.parametrize(
    "original_message,expectation",  # type: ignore
    [
        ("some random message", does_not_raise()),
        (f"{SipTriggers.SIP_HANGUP.value}", pytest.raises(KeyError)),
        (f"{SipTriggers.SIP_HUMAN_HANDOVER.value}", pytest.raises(ValueError)),
        (f"{SipTriggers.SIP_SEND_NOW.value}", does_not_raise()),
        (f"{QueryTriggers.REPLACEMENT_TRIGGER.value}", does_not_raise()),
    ],
)
def test_trigger_functions(original_message, expectation):
    response = create_text_response(original_message)
    message_handler = TestMessageHandler()
    with expectation:
        response = message_handler.process_messages(response)


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("some random message", "some random message"),
        ("<SIP:SEND_NOW=('something')> at start", "something at start"),
        ("<SIP:PAUSE=('5s')> at start", " at start"),
        (
            "triggers <SIP:SEND_NOW=('trigger1')> aplenty <SIP:SEND_NOW=('trigger2')> different kinds <SIP:PAUSE=('10s')>",
            "triggers trigger2 aplenty trigger1 different kinds ",
        ),
        ("<c-examination.appointment_date>", REPLACEMENT_STRING),
        (
            "<c-examination.appointment_date> <c-examination.appointment_date>",
            f"{REPLACEMENT_STRING} {REPLACEMENT_STRING}",
        ),
    ],
)
def test_trigger_functions_replacement(original_message, processed_message):
    response = create_text_response(original_message)
    message_handler = TestMessageHandler()
    response = message_handler.process_messages(response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("2012-12-12T00:00:00", "12.12.2012"),
        ("hello 2012-12-12T00:00:00 hello", "hello 12.12.2012 hello"),
        ("there 2012-12-12T00:00:00 there", "there 12.12.2012 there"),
    ],
)
def test_reformat_date(original_message, processed_message):
    response = create_text_response(original_message)
    assert response.query_result.fulfillment_messages[0].text.text[0] == original_message
    MessageHandler.reformat_date(response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("12.12.2012T00:00:00", "12.12.2012T00:00"),
        ("hello 12.12.2012T00:00:00 hello", "hello 12.12.2012T00:00 hello"),
        ("hello 00:00:00 hello", "hello 00:00 hello"),
        ("hello 16:20:00 hello", "hello 16:20 hello"),
    ],
)
def test_strip_seconds(original_message, processed_message):
    response = create_text_response(original_message)
    assert response.query_result.fulfillment_messages[0].text.text[0] == original_message
    MessageHandler.strip_seconds(response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("12.12.2012", "Wednesday the 12.12.2012"),
        ("11.12.2012", "Tuesday the 11.12.2012"),
        ("13.12.2012T16:00:00", "Thursday the 13.12.2012T16:00:00"),
    ],
)
def test_adding_days_english(original_message, processed_message):
    response = create_text_response(original_message)
    assert response.query_result.fulfillment_messages[0].text.text[0] == original_message
    MessageHandler.add_weekday(response, EnglishDays)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("12.12.2012", "Mittwoch der 12.12.2012"),
        ("11.12.2012", "Dienstag der 11.12.2012"),
        ("13.12.2012T16:00:00", "Donnerstag der 13.12.2012T16:00:00"),
    ],
)
def test_adding_days_german(original_message, processed_message):
    response = create_text_response(original_message)
    assert response.query_result.fulfillment_messages[0].text.text[0] == original_message
    MessageHandler.add_weekday(response, GermanDays)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message


@pytest.mark.parametrize(
    "original_message,processed_message",  # type: ignore
    [
        ("12.12.2012", "Mittwoch der 12.12.2012"),
        ("11.12.2012", "Dienstag der 11.12.2012"),
        ("13.12.2012T16:00:00", "Donnerstag der 13.12.2012T16:00:00"),
    ],
)
def test_adding_days_default(original_message, processed_message):
    response = create_text_response(original_message)
    assert response.query_result.fulfillment_messages[0].text.text[0] == original_message
    MessageHandler.add_weekday(response)
    assert response.query_result.fulfillment_messages[0].text.text[0] == processed_message
