# tap_consumer/__init__.py - TAP-Consumer
# Based on TAP.py - TAP parser
# Modified to ignore non-TAP input and handle YAML diagnostics
# Copyright 2024, Eden Ross Duff, MSc
# A pyparsing parser to process the output of the Perl "Test Anything Protocol"
# (https://metacpan.org/pod/release/PETDANCE/TAP-1.00/TAP.pm)
#
# Copyright 2008, by Paul McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from typing import Mapping
from typing import TypeAlias

from pyparsing import ParserElement
from pyparsing import ParseResults

__all__ = ['tap_document', 'TAPTest', 'TAPSummary']

Diagnostics: TypeAlias = Mapping[
    int | str, str | list[Mapping[int | str, str]] | Mapping[int | str, str]
]
tap_document: ParserElement

class TAPTest:
    """A single TAP test point."""
    num: int
    description: str | None
    passed: str
    skipped: bool
    todo: bool
    yaml: Diagnostics
    def __init__(self, results: ParseResults) -> None:
        """Create a test point.

        :param results: parsed TAP stream
        :type results: ParseResults
        """
    @classmethod
    def bailed_test(cls, num: int) -> TAPTest:
        """Create a bailed test.

        :param num: the test number
        :type num: int
        :return: a bailed TAPTest object
        :rtype: TAPTest
        """

class TAPSummary:
    """Summarize a parsed TAP stream."""
    passed_tests: list[TAPTest]
    failed_tests: list[TAPTest]
    skipped_tests: list[TAPTest]
    todo_tests: list[TAPTest]
    bonus_tests: list[TAPTest]
    yaml_diagnostics: Diagnostics
    bail: bool
    version: int
    bail_reason: str
    passed_suite: bool
    def __init__(self, results: ParseResults) -> None:
        """Initialize with parsed TAP data.

        :param results: A parsed TAP stream
        :type results: ParseResults
        """
    def summary(self, show_passed: bool = False, show_all: bool = False) -> str:
        """Get the summary of a TAP stream.

        :param show_passed: show passed tests, defaults to False
        :type show_passed: bool, optional
        :param show_all: show all results, defaults to False
        :type show_all: bool, optional
        :return: a text summary of a TAP stream
        :rtype: str
        """
