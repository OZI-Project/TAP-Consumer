# tap_consumer/__init__.py - TAP-Consumer
#
# Based on TAP.py - TAP parser
#
# A pyparsing parser to process the output of the Perl
#   "Test Anything Protocol"
#   (https://metacpan.org/pod/release/PETDANCE/TAP-1.00/TAP.pm)
# Copyright 2008, by Paul McGuire
#
# Modified to ignore non-TAP input and handle YAML diagnostics
# Copyright 2024, Eden Ross Duff, MSc
import sys

import yaml
from pyparsing import CaselessLiteral
from pyparsing import FollowedBy
from pyparsing import Group
from pyparsing import LineEnd
from pyparsing import Literal
from pyparsing import OneOrMore
from pyparsing import Optional
from pyparsing import ParserElement
from pyparsing import ParseResults
from pyparsing import Regex
from pyparsing import SkipTo
from pyparsing import Suppress
from pyparsing import Word
from pyparsing import empty
from pyparsing import nums
from pyparsing import rest_of_line

if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import Self  # noqa: TC002
elif sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self  # noqa: TC002

__all__ = ['tap_parser', 'TAPTest', 'TAPSummary']

# newlines are significant whitespace, so set default skippable
# whitespace to just spaces and tabs
ParserElement.set_default_whitespace_chars(' \t')
NL = LineEnd().suppress()  # type: ignore

integer = Word(nums)
plan = '1..' + integer('ubound')

OK, NOT_OK = map(Literal, ['ok', 'not ok'])
test_status = OK | NOT_OK

description = Regex('[^#\n]+')
description.set_parse_action(lambda t: t[0].lstrip('- '))  # pyright: ignore

TODO, SKIP = map(CaselessLiteral, 'TODO SKIP'.split())  # noqa: T101
directive = Group(
    Suppress('#')
    + (
        TODO + rest_of_line  # noqa: T101
        | FollowedBy(SKIP) + rest_of_line.copy().set_parse_action(lambda t: ['SKIP', t[0]])
    ),
)

commentLine = Suppress('#') + empty + rest_of_line
version = Suppress('TAP version') + Word(nums[1:], nums, as_keyword=True)
yaml_end = Suppress('...')
test_line = Group(
    Optional(OneOrMore(commentLine + NL))('comments')
    + test_status('passed')
    + Optional(integer)('test_number')
    + Optional(description)('description')
    + Optional(directive)('directive')
    + Optional(
        NL
        + Group(
            Suppress('---')
            + SkipTo(yaml_end)('yaml').set_parse_action(
                lambda t: yaml.safe_load(t[0])  # pyright: ignore
            )
            + yaml_end,
        ),
    ),
)
bail_line = Group(Literal('Bail out!')('BAIL') + empty + Optional(rest_of_line)('reason'))

tap_parser = Optional(Group(Suppress(SkipTo(version)) + version)('version') + NL) + Optional(
    Group(plan)('plan') + NL,
) & Group(OneOrMore((test_line | Suppress(SkipTo(test_line)) + test_line | bail_line) + NL))(
    'tests',
)


class TAPTest:
    def __init__(self: Self, results: ParseResults) -> None:
        self.num = results.test_number
        self.passed = results.passed == 'ok'
        self.skipped = self.todo = False
        if results.directive:
            self.skipped = results.directive[0][0] == 'SKIP'
            self.todo = results.directive[0][0] == 'TODO'  # noqa: T101

    @classmethod
    def bailed_test(cls: type[Self], num: int) -> 'TAPTest':
        ret = TAPTest(empty.parse_string(''))
        ret.num = num
        ret.skipped = True
        return ret


class TAPSummary:
    def __init__(self: Self, results: ParseResults) -> None:  # noqa: C901
        self.passed_tests = []
        self.failed_tests = []
        self.skipped_tests = []
        self.todo_tests = []
        self.bonus_tests = []
        self.bail = False
        self.version = results.version[0] if results.version else 12
        if results.plan:
            expected = list(range(1, int(results.plan.ubound) + 1))  # pyright: ignore
        else:
            expected = list(range(1, len(results.tests) + 1))
        print(results.tests)
        for i, res in enumerate(results.tests):
            # test for bail out
            if res.BAIL:  # pyright: ignore
                # ~ print "Test suite aborted: " + res.reason
                # ~ self.failedTests += expected[i:]
                self.bail = True
                self.skipped_tests += [TAPTest.bailed_test(ii) for ii in expected[i:]]
                self.bailReason = res.reason  # pyright: ignore
                break

            testnum = i + 1
            if res.testNumber != '':  # pragma: no cover  # pyright: ignore
                if testnum != int(res.testNumber):  # pyright: ignore
                    print('ERROR! test %(testNumber)s out of sequence' % res)
                testnum = int(res.testNumber)  # pyright: ignore
            res['testNumber'] = testnum  # pyright: ignore

            test = TAPTest(res)  # pyright: ignore
            if test.passed:
                self.passed_tests.append(test)
            else:
                self.failed_tests.append(test)
            if test.skipped:
                self.skipped_tests.append(test)
            if test.todo:
                self.todo_tests.append(test)
            if test.todo and test.passed:
                self.bonus_tests.append(test)

        self.passedSuite = not self.bail and (
            set(self.failed_tests) - set(self.todo_tests) == set()
        )

    def summary(  # noqa: C901
        self: Self, showPassed: bool = False, showAll: bool = False
    ) -> str:
        testListStr = lambda tl: '[' + ','.join(str(t.num) for t in tl) + ']'  # noqa: E731
        summaryText = [f'TAP version: {self.version}']
        if showPassed or showAll:
            summaryText.append(f'PASSED: {testListStr(self.passed_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.failed_tests or showAll:
            summaryText.append(f'FAILED: {testListStr(self.failed_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.skipped_tests or showAll:
            summaryText.append(f'SKIPPED: {testListStr(self.skipped_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.todo_tests or showAll:
            summaryText.append(
                f'TODO: {testListStr(self.todo_tests)}'  # type: ignore  # noqa: T101
            )
        else:  # pragma: no cover
            pass
        if self.bonus_tests or showAll:
            summaryText.append(f'BONUS: {testListStr(self.bonus_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.passedSuite:
            summaryText.append('PASSED')
        else:
            summaryText.append('FAILED')
        return '\n'.join(summaryText)


# create TAPSummary objects from tapOutput parsed results, by setting
# class as parse action
tap_parser.set_parse_action(TAPSummary)
