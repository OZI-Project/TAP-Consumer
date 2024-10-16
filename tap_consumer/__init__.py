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

from pyparsing import (
    Each,
    Keyword,
    ParserElement,
    LineEnd,
    Optional,
    SkipTo,
    Word,
    ZeroOrMore,
    dict_of,
    nums,
    Regex,
    Literal,
    CaselessLiteral,
    Group,
    OneOrMore,
    Suppress,
    restOfLine,
    FollowedBy,
    empty,
)
import yaml

__all__ = ["tap_parser", "TAPTest", "TAPSummary"]

# newlines are significant whitespace, so set default skippable
# whitespace to just spaces and tabs
ParserElement.setDefaultWhitespaceChars(" \t")
NL = LineEnd().suppress()

integer = Word(nums)
plan = "1.." + integer("ubound")

OK, NOT_OK = map(Literal, ["ok", "not ok"])
testStatus = OK | NOT_OK

description = Regex("[^#\n]+")
description.setParseAction(lambda t: t[0].lstrip("- ")) # type: ignore

TODO, SKIP = map(CaselessLiteral, "TODO SKIP".split())
directive = Group(
    Suppress("#")
    + (
        TODO + restOfLine
        | FollowedBy(SKIP) + restOfLine.copy().setParseAction(lambda t: ["SKIP", t[0]])
    )
)

commentLine = Suppress("#") + empty + restOfLine
version = Suppress('TAP version') + Word(nums[1:], nums, as_keyword=True)
yaml_end = Suppress('...')
testLine = Group(
    Optional(OneOrMore(commentLine + NL))("comments")
    + testStatus("passed")
    + Optional(integer)("testNumber")
    + Optional(description)("description")
    + Optional(directive)("directive")
    + Optional(NL + Group(Suppress('---') + SkipTo(yaml_end)('yaml').set_parse_action(lambda t: yaml.safe_load(t[0])) + yaml_end))
)
bailLine = Group(Literal("Bail out!")("BAIL") + empty + Optional(restOfLine)("reason"))

tap_parser = Optional(Group(Suppress(SkipTo(version)) + version)('version') + NL) + Optional(Group(plan)("plan") + NL) & Group(
    OneOrMore((testLine | Suppress(SkipTo(testLine)) + testLine | bailLine ) + NL)
)("tests")

class TAPTest:
    def __init__(self, results):
        self.num = results.testNumber
        self.passed = results.passed == "ok"
        self.skipped = self.todo = False
        if results.directive:
            self.skipped = results.directive[0][0] == "SKIP"
            self.todo = results.directive[0][0] == "TODO"

    @classmethod
    def bailedTest(cls, num):
        ret = TAPTest(empty.parseString(""))
        ret.num = num
        ret.skipped = True
        return ret


class TAPSummary:
    def __init__(self, results):
        self.passedTests = []
        self.failedTests = []
        self.skippedTests = []
        self.todoTests = []
        self.bonusTests = []
        self.bail = False
        self.version = results.version[0] if results.version else 12
        if results.plan:
            expected = list(range(1, int(results.plan.ubound) + 1))
        else:
            expected = list(range(1, len(results.tests) + 1))
        print(results.tests)
        for i, res in enumerate(results.tests):
            # test for bail out
            if res.BAIL:
                # ~ print "Test suite aborted: " + res.reason
                # ~ self.failedTests += expected[i:]
                self.bail = True
                self.skippedTests += [TAPTest.bailedTest(ii) for ii in expected[i:]]
                self.bailReason = res.reason
                break

            testnum = i + 1
            if res.testNumber != "":
                if testnum != int(res.testNumber):
                    print("ERROR! test %(testNumber)s out of sequence" % res)
                testnum = int(res.testNumber)
            res["testNumber"] = testnum

            test = TAPTest(res)
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

    def summary(self, showPassed=False, showAll=False):
        testListStr = lambda tl: "[" + ",".join(str(t.num) for t in tl) + "]"
        summaryText = [f'TAP version: {self.version}']
        if showPassed or showAll:
            summaryText.append(f"PASSED: {testListStr(self.passedTests)}")
        if self.failedTests or showAll:
            summaryText.append(f"FAILED: {testListStr(self.failedTests)}")
        if self.skippedTests or showAll:
            summaryText.append(f"SKIPPED: {testListStr(self.skippedTests)}")
        if self.todoTests or showAll:
            summaryText.append(f"TODO: {testListStr(self.todoTests)}")
        if self.bonusTests or showAll:
            summaryText.append(f"BONUS: {testListStr(self.bonusTests)}")
        if self.passedSuite:
            summaryText.append("PASSED")
        else:
            summaryText.append("FAILED")
        return "\n".join(summaryText)


# create TAPSummary objects from tapOutput parsed results, by setting
# class as parse action
tap_parser.setParseAction(TAPSummary)


def main():
    test1 = """\
foo bar
TAP version 14
baz
1..4
ok 1 - Input file opened
not ok 2 - First line of the input valid
ok 3 - Read the rest of the file
not ok 4 - Summarized correctly # TODO Not written yet
        """
    test2 = """\
ok 1
not ok 2 some description # TODO with a directive
ok 3 a description only, no directive
ok 4 # TODO directive only
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
    
    ...
ok
ok
ssssssssssssssssssss
ok
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
1..9
        """
    test4 = """\
1..4
ok 1 - Creating test program
ok 2 - Test program runs, no error
not ok 3 - infinite loop # TODO halting problem unsolved
not ok 4 - infinite loop 2 # TODO halting problem unsolved
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
not ok 4 - pinged sapphire
ok 5 - pinged onyx
not ok 6 - pinged quartz
ok 7 - pinged gold
1..7
        """

    for test in (test1, test2, test3, test4, test5, test6):
        print(test)
        tapResult = tap_parser.parse_string(test)[0]
        print(tapResult.summary(showAll=True)) # type: ignore
        print()


if __name__ == "__main__":
    main()