import os

from click.testing import CliRunner

from r2b2.cli import cli

# TODO: Test multiple round execution patterns
# TODO: Test all combinations of audit parameters and contest file
# TODO: Test election mode (once implemented)
# TODO: Test election file parsing (once election mode working)


def test_interactive_simple():
    """Testing `r2b2 interactive`

    Simple test of interactive module where contest and audit creation occur without error
    The audit should run and stop in the first round.
    """
    runner = CliRunner()
    user_in = 'brla\n0.1\n0.2\n1000\n2\nA\n700\nB\n300\n1\nA\nPLURALITY\ny\ny\n200\n175\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_interactive_given_audit():
    """Testing `r2b2 interactive -a brla -r 0.1 -m 0.2`

    Test of interactive module where audit type, risk limit, and max fraction to draw are given
    as cli option arguments. The audit should run and stop in the first round.
    """
    runner = CliRunner()
    user_in = '1000\n2\nA\n700\nB\n300\n1\nA\nPLURALITY\ny\ny\n200\n175\n'
    result = runner.invoke(cli, 'interactive -a brla -r 0.1 -m 0.2', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_given_audit.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_interactive_given_contest():
    """Testing `r2b2 interactive --contest-file=/.../single_contest_template.json`

    Test of interactive module where contest is given as a JSON file and parsed into Contest object.
    The audit should run and stop in the first round.
    """
    runner = CliRunner()
    user_in = 'brla\n0.1\n0.2\ny\ny\n20\n19\n'
    result = runner.invoke(cli, 'interactive --contest-file=src/r2b2/tests/data/single_contest_template.json', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_given_contest.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_interactive_given_both():
    """Testng `r2b2 interactive  -a brla -r 0.1 -m 0.2 --contest-file=/.../single_contest_template.json`

    Test of interactive module where contest JSON file and audit parameters are given as cli
    arguments. The audit should run and stop in the first round.
    """
    runner = CliRunner()
    user_in = 'y\ny\n20\n19\n'
    result = runner.invoke(cli,
                           'interactive -a brla -r 0.1 -m 0.2 --contest-file src/r2b2/tests/data/single_contest_template.json',
                           input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_given_both.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_interactive_multi_round():
    """Testing `r2b2 interactive -a blra -r 0.1 -m 0.1 --contest-file=/.../basic_contest.json`"""

    runner = CliRunner()
    user_in = 'y\ny\n100\n63\nn\n200\n119\nn\n300\n175\n'
    result = runner.invoke(cli, 'interactive --contest-file src/r2b2/tests/data/basic_contest.json -a brla -r 0.1 -m 0.1', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_multiround_.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_bulk_min_to_max():
    """Testing `r2b2 bulk /.../single_contest_template.json brla -r 0.1 -m 0.4`"""
    runner = CliRunner()
    result = runner.invoke(cli, 'bulk src/r2b2/tests/data/single_contest_template.json brla 0.1 0.4')
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_bulk_min_to_max.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_bulk_round_list():
    """Testing `r2b2 bulk -l '100 200 300' /.../basic_contest.json brla 0.1 0.05 `"""
    runner = CliRunner()
    result = runner.invoke(cli, 'bulk -l \'100 200 300 400 500\' src/r2b2/tests/data/basic_contest.json brla 0.1 0.05')
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_bulk_rounds.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_template_contest():
    """Testing `r2b2 template contest`"""
    runner = CliRunner()
    result = runner.invoke(cli, 'template contest')
    output_file = open('src/r2b2/tests/data/single_contest_template.json', 'r')
    expected_out = '\nWelcome to the R2B2 auditing tool!\n\n' + str(output_file.read()) + '\n'
    assert result.output == expected_out
    output_file.close()


def test_tempalte_election():
    """Testing `r2b2 template election`"""
    runner = CliRunner()
    result = runner.invoke(cli, 'template election')
    output_file = open('src/r2b2/tests/data/election_template.json', 'r')
    expected_out = '\nWelcome to the R2B2 auditing tool!\n\n' + str(output_file.read()) + '\n'
    assert result.output == expected_out
    output_file.close()


def test_template_contest_output_file():
    """Testing `r2b2 template -o test_contest.json contest`"""
    runner = CliRunner()
    result = runner.invoke(cli, 'template -o test_contest.json contest')
    output_file = open('src/r2b2/tests/data/single_contest_template.json', 'r')
    test_output_file = open('test_contest.json', 'r')
    expected_out = '\nWelcome to the R2B2 auditing tool!\n\nTemplate written to test_contest.json\n'
    expected_out_file = output_file.read()
    result_output_file = test_output_file.read()
    assert result.output == expected_out
    assert result_output_file == expected_out_file
    os.remove('test_contest.json')
    output_file.close()


def test_tempalte_election_output_file():
    """Testing `r2b2 template -o test_election.json election`"""
    runner = CliRunner()
    result = runner.invoke(cli, 'template -o test_election.json election')
    output_file = open('src/r2b2/tests/data/election_template.json', 'r')
    test_output_file = open('test_election.json', 'r')
    expected_out = '\nWelcome to the R2B2 auditing tool!\n\nTemplate written to test_election.json\n'
    expected_out_file = output_file.read()
    result_output_file = test_output_file.read()
    assert result.output == expected_out
    assert result_output_file == expected_out_file
    os.remove('test_election.json')
    output_file.close()
