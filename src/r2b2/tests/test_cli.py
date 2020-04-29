from io import StringIO

from r2b2.cli import main

# TODO: Test multiple round execution patterns
# TODO: Test all combinations of audit parameters and contest file
# TODO: Test election mode (once implemented)
# TODO: Test election file parsing (once election mode working)


def test_interactive_simple(monkeypatch, capsys):
    """Testing `r2b2 -i`

    Simple test of interactive module where contest and audit creation occur without error
    The audit should run and stop in the first round.
    """
    user_in = StringIO('1000\n2\nA\n700\nB\n300\n1\nA\n0\n0.1\n0.2\n1\n200\n175\n')
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive.txt', 'r')
    expected_out = output_file.read()
    monkeypatch.setattr('sys.stdin', user_in)
    main(['-i'])
    captured = capsys.readouterr()
    assert captured.out == expected_out
    output_file.close()


def test_interactive_given_audit(monkeypatch, capsys):
    """Testing `r2b2 -i -a=brla -r=0.1 -m=0.2`

    Test of interactive module where audit type, risk limit, and max fraction to draw are given
    as cli arguments. The audit should run and stop in the first round.
    """
    user_in = StringIO('1000\n2\nA\n700\nB\n300\n1\nA\n0\n200\n175\n')
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_given_audit.txt', 'r')
    expected_out = output_file.read()
    monkeypatch.setattr('sys.stdin', user_in)
    main(['-i', '-a=brla', '-r=0.1', '-m=0.2'])
    captured = capsys.readouterr()
    assert captured.out == expected_out
    output_file.close()


def test_interactive_given_contest(monkeypatch, capsys):
    """Testing `r2b2 -i --contest_file=/.../single_contest_template.json`

    Test of interactive module where contest is given as a JSON file and parsed into Contest object.
    The audit should run and stop in the first round.
    """
    user_in = StringIO('0.1\n0.2\n1\n20\n19\n')
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_given_contest.txt', 'r')
    expected_out = output_file.read()
    monkeypatch.setattr('sys.stdin', user_in)
    main(['-i', '--contest_file=src/r2b2/tests/data/single_contest_template.json'])
    captured = capsys.readouterr()
    assert captured.out == expected_out
    output_file.close()


def test_interactive_given_both(monkeypatch, capsys):
    """Testng `r2b2 -i -a=brla -r=0.1 -m=0.2 --contest_file=/.../single_contest_template.json`

    Test of interactive module where contest JSON file and audit parameters are given as cli
    arguments. The audit should run and stop in the first round.
    """
    user_in = StringIO('20\n19\n')
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_given_both.txt', 'r')
    expected_out = output_file.read()
    monkeypatch.setattr('sys.stdin', user_in)
    main(['-i', '-a=brla', '-r=0.1', '-m=0.2', '--contest_file=src/r2b2/tests/data/single_contest_template.json'])
    captured = capsys.readouterr()
    assert captured.out == expected_out
    output_file.close()


def test_bulk_min_to_max(capsys):
    """Testing `r2b2 -a brla -r 0.1 -m 0.4 --contest_file=/.../single_contest_template.json`"""
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_bulk_min_to_max.txt', 'r')
    expected_out = output_file.read()
    main(['-a=brla', '-r=0.1', '-m=0.4', '--contest_file=src/r2b2/tests/data/single_contest_template.json'])
    captured = capsys.readouterr()
    assert captured.out == expected_out
    output_file.close()
