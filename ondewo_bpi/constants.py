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

from enum import Enum

DATE_FORMAT: str = r"%d.%m.%4Y"
DATE_FORMAT_BACK: str = r"%d.%m.%Y"
TIME_FORMAT: str = r"%H:%M:%S"


class SipTriggers(Enum):
    SIP_HANGUP: str = "<SIP:HANGUP>"
    SIP_HUMAN_HANDOVER: str = "<SIP:HUMAN_HANDOVER=(.*?)>"
    SIP_SEND_NOW: str = "<SIP:SEND_NOW=(.*?)>"
    SIP_PAUSE: str = "<SIP:PAUSE=(.*?)>"


class QueryTriggers(Enum):
    REPLACEMENT_TRIGGER: str = r"<(\w*-\w*\.\w*)>"


class GermanDays(Enum):
    sun: str = 'Sontag der '
    mon: str = 'Montag der '
    tue: str = 'Dienstag der '
    wed: str = 'Mittwoch der '
    thur: str = 'Donnerstag der '
    fri: str = 'Freitag der '
    sat: str = 'Samstag der '


class EnglishDays(Enum):
    sun: str = 'Sunday the '
    mon: str = 'Monday the '
    tue: str = 'Tuesday the '
    wed: str = 'Wednesday the '
    thur: str = 'Thursday the '
    fri: str = 'Friday the '
    sat: str = 'Saturday the '
