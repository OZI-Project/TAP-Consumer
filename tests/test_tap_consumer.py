# noqa: INP001
from tap_consumer import tap_parser


def test_examples() -> None:
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

    for test in (test1, test2, test3, test4, test5, test6):
        print(test)
        tapResult = tap_parser.parse_string(test)[0]
        print(tapResult.summary(show_all=True))  # pyright: ignore
        print()
