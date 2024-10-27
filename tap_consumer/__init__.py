# tap_consumer/__init__.py - TAP-Consumer
#
# Based on TAP.py - TAP parser
#
# A pyparsing parser to process the output of the Perl
#   "Test Anything Protocol"
#   (https://metacpan.org/pod/release/PETDANCE/TAP-1.00/TAP.pm)
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
#
# Modified to ignore non-TAP input and handle YAML diagnostics
# Copyright 2024, Eden Ross Duff, MSc
import sys
from typing import Mapping
from typing import TypeAlias

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
from pyparsing import White
from pyparsing import Word
from pyparsing import ZeroOrMore
from pyparsing import empty
from pyparsing import nums
from pyparsing import rest_of_line

if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import Self  # noqa: TC002
elif sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self  # noqa: TC002

__all__ = ['tap_document', 'TAPTest', 'TAPSummary']

Diagnostics: TypeAlias = Mapping[
    int | str, str | list[Mapping[int | str, str]] | Mapping[int | str, str]
]
# newlines are significant whitespace, so set default skippable
# whitespace to just spaces and tabs
ParserElement.set_default_whitespace_chars(' \t')
NL = LineEnd().suppress()  # type: ignore
INDENT4 = OneOrMore(White(' ', exact=4))
INDENT3 = Suppress(OneOrMore(White(' ', exact=3)))
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
comment_line = Suppress('#' + White(' ')) + rest_of_line
version = Suppress('TAP version') + Word(nums[1:], nums, as_keyword=True)
yaml_end = Suppress('...')
test_line = Group(
    ZeroOrMore(White(' ', exact=4).leave_whitespace()).set_parse_action(
        lambda t: len(t.as_list())
    )('subtest_level')
    + test_status('passed')
    + Optional(integer)('test_number')
    + Optional(description)('description')
    + Optional(directive)('directive')
    + Optional(
        NL
        + Group(
            Suppress('---')
            + SkipTo(yaml_end).set_parse_action(
                lambda t: yaml.safe_load(t[0])  # pyright: ignore
            )
            + yaml_end,
        )('yaml').set_parse_action(lambda t: t.as_dict()),
    )
)

bail_line = Group(
    CaselessLiteral('Bail out!')('BAIL') + empty + Optional(rest_of_line)('reason')
)
comment = Optional(comment_line)('comments')
anything = Suppress(SkipTo(NL))
tap_document = Optional(
    Group(Suppress(SkipTo(version)) + version)('version') + NL
) + Optional(
    Group(plan)('plan') + NL,
) & Group(
    OneOrMore((test_line | bail_line | anything | comment) + NL)
)(
    'tests',
)


class TAPTest:
    """A single TAP test point."""

    def __init__(self: Self, results: ParseResults) -> None:
        """Create a test point.

        :param results: parsed TAP stream
        :type results: ParseResults
        """
        self.subtest_level = results.subtest_level
        self.num = results.test_number
        self.description = results.description if results.description else None
        self.passed = results.passed == 'ok'
        self.skipped = self.todo = False
        if results.directive:
            self.skipped = results.directive[0][0] == 'SKIP'
            self.todo = results.directive[0][0] == 'TODO'  # noqa: T101
        self.yaml = results.yaml['yaml'] if results.yaml else {}  # pyright: ignore

    @classmethod
    def bailed_test(cls: type[Self], num: int) -> 'TAPTest':
        """Create a bailed test.

        :param num: the test number
        :type num: int
        :return: a bailed TAPTest object
        :rtype: TAPTest
        """
        ret = TAPTest(empty.parse_string(''))
        ret.num = num
        ret.skipped = True
        return ret


class TAPSummary:
    """Summarize a parsed TAP stream."""

    def __init__(self: Self, results: ParseResults) -> None:  # noqa: C901
        """Initialize with parsed TAP data.

        :param results: A parsed TAP stream
        :type results: ParseResults
        """
        self.passed_tests: list[TAPTest] = []
        self.subtests: list[TAPTest] = []
        self.failed_tests: list[TAPTest] = []
        self.skipped_tests: list[TAPTest] = []
        self.todo_tests: list[TAPTest] = []
        self.bonus_tests: list[TAPTest] = []
        self.yaml_diagnostics: Diagnostics = {}
        self.bail = False
        self.version = results.version[0] if results.version else 12
        if results.plan:
            expected = list(range(1, int(results.plan.ubound) + 1))  # pyright: ignore
        else:
            expected = list(range(1, len(results.tests) + 1))
        subtestnum = 0
        for i, res in enumerate(results.tests):
            # test for bail out
            if hasattr(res, 'BAIL') and res.BAIL:  # pyright: ignore
                # ~ print "Test suite aborted: " + res.reason
                # ~ self.failed_tests += expected[i:]
                self.bail = True
                self.skipped_tests += [TAPTest.bailed_test(ii) for ii in expected[i:]]
                self.bail_reason = res.reason  # pyright: ignore
                break

            if res.subtest_level > 0:  # pyright: ignore
                subtestnum += 1
                self.subtests.append(TAPTest(res))  # pyright: ignore
                continue

            testnum = i + 1
            if res.test_number != '':  # pragma: no cover  # pyright: ignore
                if testnum - subtestnum != int(res.test_number):  # pyright: ignore
                    print('ERROR! test %(test_number)s out of sequence' % res)
                testnum = int(res.test_number)  # pyright: ignore
            res['test_number'] = testnum  # pyright: ignore

            test = TAPTest(res)  # pyright: ignore
            if test.yaml:
                self.yaml_diagnostics.update({testnum: test.yaml[0]})  # type: ignore
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

        self.passed_suite = not self.bail and (
            set(self.failed_tests) - set(self.todo_tests) == set()
        )

    def summary(  # noqa: C901
        self: Self,
        show_passed: bool = False,
        show_all: bool = False,
    ) -> str:
        """Get the summary of a TAP stream.

        :param show_passed: show passed tests, defaults to False
        :type show_passed: bool, optional
        :param show_all: show all results, defaults to False
        :type show_all: bool, optional
        :return: a text summary of a TAP stream
        :rtype: str
        """
        test_list_str = lambda tl: '[' + ','.join(str(t.num) for t in tl) + ']'  # noqa: E731
        summary_text = []
        if show_passed or show_all:
            summary_text.append(f'PASSED: {test_list_str(self.passed_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.failed_tests or show_all:
            summary_text.append(f'FAILED: {test_list_str(self.failed_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.skipped_tests or show_all:
            summary_text.append(f'SKIPPED: {test_list_str(self.skipped_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.todo_tests or show_all:
            summary_text.append(
                f'TODO: {test_list_str(self.todo_tests)}'  # type: ignore  # noqa: T101
            )
        else:  # pragma: no cover
            pass
        if self.bonus_tests or show_all:
            summary_text.append(f'BONUS: {test_list_str(self.bonus_tests)}')  # type: ignore
        else:  # pragma: no cover
            pass
        if self.yaml_diagnostics:
            summary_text.append(
                yaml.safe_dump(
                    self.yaml_diagnostics, explicit_start=True, explicit_end=True
                ).strip()
            )
        else:  # pragma: no cover
            pass
        if self.passed_suite:
            summary_text.append('PASSED')
        else:
            summary_text.append('FAILED')
        return '\n'.join(summary_text)


tap_document.set_parse_action(TAPSummary)

if __name__ == '__main__':
    test1 = """\
foo bar
TAP version 14
baz
1..4
ok 1 - Input file opened
not ok 2 - First line of the input valid
ok 3 - Read the rest of the file
not ok 4 - Summarized correctly # SKIP Not written yet
"""
    test2 = """\
ok 1
not ok 2 some description # SKIP with a directive
ok 3 a description only, no directive
ok 4 # TODO directive only # noqa: T101
ok a description only, no directive
ok # Skipped only a directive, no description
ok
"""
    test3 = """\
ok - created Board
ok
ok
not ok
   ---
   yaml-key: val
   ...
ok
ok
# Subtest: x  # noqa: E800
    1..1
    ok
ssssssssssssssssssss
ok
   ---
   yaml-key2:
      nested-yaml-key: val
   ...
ok
# +------+------+------+------+
# |      |16G   |      |05C   |
# |      |G N C |      |C C G |
# |      |  G   |      |  C  +|
# +------+------+------+------+
# |10C   |01G   |      |03C   |
# |R N G |G A G |      |C C C |
# |  R   |  G   |      |  C  +|
# +------+------+------+------+
# |      |01G   |17C   |00C   |
# |      |G A G |G N R |R N R |
# |      |  G   |  R   |  G   |
# +------+------+------+------+
ok - board has 7 tiles + starter tile
1..10
"""
    test4 = """\
1..4
ok 1 - Creating test program
ok 2 - Test program runs, no error
not ok 3 - infinite loop
not ok 4 - infinite loop 2
"""
    test5 = """\
1..20
ok - database handle
not ok - failed database login
Bail out! Couldn't connect to database.
"""
    test6 = """\
ok 1 - retrieving servers from the database
# need to ping 6 servers
ok 2 - pinged diamond
ok 3 - pinged ruby
ok 4 - pinged sapphire
ok 5 - pinged onyx
ok 6 - pinged quartz
ok 7 - pinged gold
1..7
"""
    test7 = """\
TAP version 14
1..2

# Subtest: foo.tap  # noqa: E800
    1..2
    ok 1
    ok 2 - this passed
ok 1 - foo.tap

# Subtest: bar.tap
    ok 1 - object should be a Bar
    not ok 2 - object.isBar should return true
       ---
       found: false
       wanted: true
       at:
           file: test/bar.ts
           line: 43
           column: 8
       ...
    ok 3 - object can bar bears # SKIP
    1..3
not ok 2 - bar.tap
   ---
   fail: 1
   todo: 1
   ...
"""

    for test in (test1, test2, test3, test4, test5, test6, test7):
        print(test)
        tapResult = tap_document.parse_string(test)[0]
        print(tapResult.summary(show_all=True))  # pyright: ignore
        print()
