from typing import Mapping
from typing import TypeAlias

from pyparsing import ParserElement
from pyparsing import ParseResults

__all__ = ['tap_parser', 'TAPTest', 'TAPSummary']

Diagnostics: TypeAlias = Mapping[
    int | str, str | list[Mapping[int | str, str]] | Mapping[int | str, str]
]
tap_parser: ParserElement

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
