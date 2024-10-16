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
from pyparsing import restOfLine

if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import Self  # noqa: TC002
elif sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self  # noqa: TC002

__all__ = ['tap_parser', 'TAPTest', 'TAPSummary']

# newlines are significant whitespace, so set default skippable
# whitespace to just spaces and tabs
ParserElement.setDefaultWhitespaceChars(' \t')
NL = LineEnd().suppress()  # type: ignore

integer = Word(nums)
plan = '1..' + integer('ubound')

OK, NOT_OK = map(Literal, ['ok', 'not ok'])
testStatus = OK | NOT_OK

description = Regex('[^#\n]+')
description.setParseAction(lambda t: t[0].lstrip('- '))  # pyright: ignore

TODO, SKIP = map(CaselessLiteral, 'TODO SKIP'.split())  # noqa: T101
directive = Group(
    Suppress('#')
    + (
        TODO + restOfLine  # noqa: T101
        | FollowedBy(SKIP) + restOfLine.copy().setParseAction(lambda t: ['SKIP', t[0]])
    ),
)

commentLine = Suppress('#') + empty + restOfLine
version = Suppress('TAP version') + Word(nums[1:], nums, as_keyword=True)
yaml_end = Suppress('...')
testLine = Group(
    Optional(OneOrMore(commentLine + NL))('comments')
    + testStatus('passed')
    + Optional(integer)('testNumber')
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
bailLine = Group(Literal('Bail out!')('BAIL') + empty + Optional(restOfLine)('reason'))

tap_parser = Optional(Group(Suppress(SkipTo(version)) + version)('version') + NL) + Optional(
    Group(plan)('plan') + NL,
) & Group(OneOrMore((testLine | Suppress(SkipTo(testLine)) + testLine | bailLine) + NL))(
    'tests',
)


class TAPTest:
    def __init__(self: Self, results: ParseResults) -> None:
        self.num = results.testNumber
        self.passed = results.passed == 'ok'
        self.skipped = self.todo = False
        if results.directive:
            self.skipped = results.directive[0][0] == 'SKIP'
            self.todo = results.directive[0][0] == 'TODO'  # noqa: T101

    @classmethod
    def bailedTest(cls: type[Self], num: int) -> 'TAPTest':
        ret = TAPTest(empty.parseString(''))
        ret.num = num
        ret.skipped = True
        return ret


class TAPSummary:
    def __init__(self: Self, results: ParseResults) -> None:  # noqa: C901
        self.passedTests = []
        self.failedTests = []
        self.skippedTests = []
        self.todoTests = []
        self.bonusTests = []
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
                self.skippedTests += [TAPTest.bailedTest(ii) for ii in expected[i:]]
                self.bailReason = res.reason  # pyright: ignore
                break

            testnum = i + 1
            if res.testNumber != '':  # pyright: ignore
                if testnum != int(res.testNumber):  # pyright: ignore
                    print(
                        'ERROR! test %(testNumber)s out of sequence' % res
                    )  # pragma: no cover
                testnum = int(res.testNumber)  # pyright: ignore
            res['testNumber'] = testnum  # pyright: ignore

            test = TAPTest(res)  # pyright: ignore
            if test.passed:
                self.passedTests.append(test)
            else:
                self.failedTests.append(test)
            if test.skipped:
                self.skippedTests.append(test)
            if test.todo:
                self.todoTests.append(test)
            if test.todo and test.passed:
                self.bonusTests.append(test)

        self.passedSuite = not self.bail and (
            set(self.failedTests) - set(self.todoTests) == set()
        )

    def summary(  # noqa: C901
        self: Self, showPassed: bool = False, showAll: bool = False
    ) -> str:
        testListStr = lambda tl: '[' + ','.join(str(t.num) for t in tl) + ']'  # noqa: E731
        summaryText = [f'TAP version: {self.version}']
        if showPassed or showAll:
            summaryText.append(f'PASSED: {testListStr(self.passedTests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.failedTests or showAll:
            summaryText.append(f'FAILED: {testListStr(self.failedTests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.skippedTests or showAll:
            summaryText.append(f'SKIPPED: {testListStr(self.skippedTests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.todoTests or showAll:
            summaryText.append(
                f'TODO: {testListStr(self.todoTests)}'  # type: ignore  # noqa: T101
            )
        else:  # pragma: no cover
            pass
        if self.bonusTests or showAll:
            summaryText.append(f'BONUS: {testListStr(self.bonusTests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.passedSuite:
            summaryText.append('PASSED')
        else:
            summaryText.append('FAILED')
        return '\n'.join(summaryText)


# create TAPSummary objects from tapOutput parsed results, by setting
# class as parse action
tap_parser.setParseAction(TAPSummary)
