"""
R2B2's command line interface offers significant out-of-the-box functionality with
respect to executing audits and generating audit data without requiring the user to
write a single line of Python.

Note:
    Why does this file exist, and why not put this in __main__?

      You might be tempted to import things from __main__ later, but that will cause
      problems: the code will get executed twice:

      - When you run `python -m r2b2` python will execute
        ``__main__.py`` as a script. That means there won't be any
        ``r2b2.__main__`` in ``sys.modules``.
      - When you import __main__ it will get executed again (as a module) because
        there's no ``r2b2.__main__`` in ``sys.modules``.

      Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import math
from typing import Tuple

import click
import pkg_resources

from r2b2.athena import Athena
from r2b2.audit import Audit
from r2b2.brla import BayesianRLA as BRLA
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.election import Election
from r2b2.minerva import Minerva
from r2b2.tests import util


# Class for parsing space separated list of integers from command line
class IntList(click.ParamType):
    name = 'integer list'

    def convert(self, value, param, ctx):
        try:
            str_list = value.split(' ')
            return [int(i) for i in str_list]
        except TypeError:
            self.fail('Expected space separated list of integers')


INT_LIST = IntList()

# Audit type choices
# TODO: add new audit types when they become available
audit_types = click.Choice(['brla', 'minerva', 'athena'], case_sensitive=False)
# Contest type choice
contest_types = click.Choice(['PLURALITY', 'MAJORITY'])


@click.group()
def cli():
    click.echo('\nWelcome to the R2B2 auditing tool!\n')
    pass


@cli.command('interactive', short_help='Interactive audit execution.')
@click.option('-e',
              '--election-mode',
              default=False,
              is_flag=True,
              flag_value=True,
              show_default=True,
              help='Use election mode instead of single-contest mode.')
@click.option('--election-file', type=str, help='Pass election data as JSON file.')  # TODO: provide format
@click.option('--contest-file', type=str, help='Pass contest data as JSON file.')  # TODO: provide format
@click.option('-a', '--audit-type', type=audit_types, prompt='Select an audit type', help='Type of audit to execute on given contest.')
@click.option('-r',
              '--risk-limit',
              type=click.FloatRange(0.0, 1.0),
              prompt='Enter desired risk limit (e.g. use 0.1 for 10%)',
              help='Risk limit (alpha) of audit. Should be value between 0 and 1.')
@click.option('-m',
              '--max-fraction-to-draw',
              type=click.FloatRange(0.0, 1.0),
              prompt='Enter maximum fraction of ballots to draw during audit',
              help='Maximum fraction of total contest ballots that could be drawn during the audit.')
@click.option('-p',
              '--pair',
              type=str,
              nargs=2,
              default=None,
              help='Pair of candidates from the contest to audit. Ordered reported winner, reported loser.')
@click.option('-v',
              '--verbose',
              default=False,
              is_flag=True,
              flag_value=True,
              show_default=False,
              help='Provides risk and stopping probability schedule of previous rounds, minimum and  maximum sample size.')
def interactive(election_mode, election_file, contest_file, audit_type, risk_limit, max_fraction_to_draw, pair, verbose):
    """Executes an audit round by round.

    Depending on what options are passed to the interactive command, users may be prompted for
    contest results, audit type, risk limit, and/or maximum fraction of contest ballots to draw
    when initializing the contest and audit to run.

    During execution, users will enter each round
    size and results of the round's sample and subsequently receive information about the current
    state of the audit. The process continues until either the stopping conditions are met or the
    audit reaches the maximum sample size.
    \f

    For information on each option run ::

        $ r2b2 interactive --help

    Example:
        Contest results can be passed as a JSON file rather than entering the data through the
        prompt::

            $ r2b2 interactive --contest-file example_contest.json

    Tip:
        To generate a template contest JSON file run::

            $ r2b2 template contest

    Example:
        Audit parameters can be passed in as options rather than entering through the prompt::

            $ r2b2 interactive --audit-type brla --risk-limit 0.1 --max-fraction-to-draw 0.2
            $ r2b2 interactive -a brla -r 0.1 -m 0.2    // Shortened equivalent

    Example:
        Election mode allows users to enter all the results from an election then select a contest
        from the election to audit::

            $ r2b2 interactive -e
            $ r2b2 interactive -e --election-file // pass election results as JSON file.

    Warning:
        Election mode simply allows you to enter an entire election's data, then select one
        one contest from that election to run. Auditing multiple contests from an election
        concurrently is not implemented.
    """

    if election_mode:
        if election_file is not None:
            election = util.parse_election(str(election_file))
        else:
            election = input_election()

        contest_choices = click.Choice(election.contests.keys(), case_sensitive=True)
        click.echo('\n')
        click.echo(election)
        contest_name = click.prompt('Select a contest from the above election', type=contest_choices)
        contest = election.contests[contest_name]

    # Check contest file if provided, otherwise request contest input
    elif contest_file is not None:
        contest = util.parse_contest(str(contest_file))
    else:
        contest = input_contest()

    # Confirm contest, if incorrect get new input
    click.echo('\n')
    if election_mode:
        click.echo(contest_name)
    click.echo(contest)
    while not click.confirm('\nUse the above contest data?'):
        contest = input_contest()
        click.echo(contest)

    # Create audit from prompted input
    audit = input_audit(contest, risk_limit, max_fraction_to_draw, audit_type, pair)
    click.echo(audit)
    if audit_type == 'athena':
        click.echo('Delta: ' + str(audit.delta))
    # Confirm audit, if incorrect get new audit
    while not click.confirm('\nAre the audit parameters correct?'):
        audit = input_audit(contest)
        click.echo(audit)

    # Run audit
    audit.run(verbose)


@cli.command('bulk', short_help='Generate audit data for given round sizes.')
@click.option('-v',
              '--verbose',
              default=False,
              is_flag=True,
              flag_value=True,
              show_default=False,
              help='Provides risk and stopping probability schedule of previous rounds, minimum and  maximum sample size.')
@click.option('-o', '--output', type=click.File('w'), default=None, help='Write output into given file.')
@click.option('-l', '--round-list', type=INT_LIST, default=None, help='Provide a list of round sizes to generate stopping sizes for.')
@click.option('-f', '--full-audit-limit', type=int, default=None, help='Set maximum size for ballot by ballot output data.')
@click.argument('contest_file', type=str)
@click.argument('audit_type', type=audit_types)
@click.argument('risk_limit', type=click.FloatRange(0.0, 1.0))
@click.argument('max_fraction_to_draw', type=click.FloatRange(0.0, 1.0))
def bulk(audit_type, risk_limit, max_fraction_to_draw, contest_file, output, round_list, full_audit_limit, verbose):
    """Bulk auditing mode generates stopping sizes for a given fixed round schedule.

    Either provide a list of round sizes for which to generate stopping sizes or
    generate a ballot by ballot list of stopping sizes from the minimum valid sample
    size to the default maximum sample size or a specified maximum sample size.
    \f

    Args:
        contest_file: Contest results as JSON file.
        audit_type: Which audit type to use to generate stopping sizes.
        risk_limit: Risk limit (alpha) of audit.
        max_fraction_to_draw: Maximum fraction of contest ballots that could be drawm during
            the audit. Sets the default maximum size of the ballot by ballot output.

    Tip:
        To generate a template contest JSON file, run::

            $ r2b2 template contest

    Returns:
        Formatted list of rounds and their associated stopping sizes. Default execution is
        ballot by ballot from minimum valid sample size to the maximum sample size of audit.

    Example:
        To generate stopping sizes for a specific set of round sizes, provide the round sizes
        as a space separated list of integers enclosed by quotes using the round list option::

            $ r2b2 bulk -l '100 200 300' contest.json brla 0.1 0.5

    Example:
        To generate a ballot by ballot result from the minimum valid sample size to a specific
        maximum (i.e. not the maximum fraction to draw of the audit), run::

            $ r2b2 bulk -f 221 contest.json brla 0.1 0.5

    Example:
        To write the results to a file instead of to stdout, run::

            $ r2b2 bulk -o output.txt contest.json brla 0.1 0.5

    Tip:
        Generating large or compute heavy data sets can take some time. To estimate run times,
        use the verbose flag to display a progress bar::

            $ r2b2 bulk -v contest.json brla 0.1 0.5

    """
    # Parse audit and contest from arguments
    contest = util.parse_contest(contest_file)
    if audit_type == 'brla':
        audit = BRLA(risk_limit, max_fraction_to_draw, contest)
    else:
        raise click.BadArgumentUsage('No valid audit type found.')

    out = '\n{:^20}|{:^20}\n'.format('Round Sizes', 'Stopping Sizes')
    out += '--------------------|--------------------\n'
    if round_list is not None:
        kmins = audit.compute_min_winner_ballots(round_list, progress=verbose)
        for i in range(len(kmins)):
            out += '{:^20}|{:^20}\n'.format(round_list[i], kmins[i])
    elif full_audit_limit is not None:
        kmins = audit.compute_all_min_winner_ballots(full_audit_limit, progress=verbose)
        for r in range(audit.min_sample_size, full_audit_limit + 1):
            out += '{:^20}|{:^20}\n'.format(r, kmins[r - audit.min_sample_size])
    else:
        kmins = audit.compute_all_min_winner_ballots(progress=verbose)
        for r in range(audit.min_sample_size, math.ceil(max_fraction_to_draw * contest.contest_ballots) + 1):
            out += '{:^20}|{:^20}\n'.format(r, kmins[r - audit.min_sample_size])

    # Write or print output
    if output is not None:
        output.write(out)
    else:
        click.echo(out)


@cli.command('template', short_help='Generate template JSON input files')
@click.argument('style', type=click.Choice(['contest', 'election']))
@click.option('-o', '--output', type=click.File('wb'), default=None, help='Write output into given file.')
def template(style, output):
    """Generate JSON templates for possible input formats.
    \f

    Example:
        To create a contest results JSON file, first generate the template as a new JSON file::

            $ r2b2 template -o my_contest.json contest

        Now the file my_contest.json will be created and contain::

            {
                "contest_ballots" : 100,
                "tally" : {
                        "CandidateA" : 50,
                        "CandidateB" : 50
                },
                "num_winners" : 1,
                "reported_winners" : ["CandidateA"],
                "contest_type" : "PLURALITY"
            }

        Simply repopulate the fields with your contest results.
    """
    # TODO: docstring
    if style == 'contest':
        template = pkg_resources.resource_string(__name__, 'tests/data/single_contest_template.json')
    elif style == 'election':
        template = pkg_resources.resource_string(__name__, 'tests/data/election_template.json')
    else:
        raise click.BadArgumentUsage('No valid template style found')
    if output is not None:
        output.write(template)
        click.echo('Template written to {}'.format(output.name))
    else:
        click.echo(template)


def input_audit(contest: Contest,
                alpha: float = None,
                max_fraction_to_draw: float = None,
                audit_type: str = None,
                pair: Tuple[str] = None,
                delta: float = None) -> Audit:
    # Create an audit from user-input.
    click.echo('\nCreate a new Audit')
    click.echo('==================\n')

    if alpha is None:
        alpha = click.prompt('Enter the desired risk limit', type=click.FloatRange(0.0, 1.0))
    if max_fraction_to_draw is None:
        max_fraction_to_draw = click.prompt('Enter the maximum fraction of contest ballots to draw', type=click.FloatRange(0.0, 1.0))
    if audit_type is None:
        audit_type = click.prompt('Select an audit type', type=audit_types)
    if delta is None and audit_type == 'athena':
        delta = click.prompt('Enter the Athena delta value', type=click.FloatRange(0.0))
    if pair == ():
        pair = None
    if pair is None:
        if contest.num_candidates > 2 and click.confirm('Select a pair of candidates other than the top 2?'):
            rw = click.prompt('Enter reported winner', type=click.Choice(contest.reported_winners))
            other_candidates = contest.candidates.copy()
            other_candidates.remove(rw)
            rl = click.prompt('Enter reported loser', type=click.Choice(other_candidates))
            pair = [rw, rl]
    else:
        pair = [pair[0], pair[1]]

    if audit_type == 'brla':
        return BRLA(alpha, max_fraction_to_draw, contest, pair)
    elif audit_type == 'minerva':
        return Minerva(alpha, max_fraction_to_draw, contest, pair)
    elif audit_type == 'athena':
        return Athena(alpha, delta, max_fraction_to_draw, contest, pair)
    # TODO: add creation for other types of audits.
    return None


def input_contest() -> Contest:
    # Creates a contest from user-input.
    click.echo('\nCreate a new Contest')
    click.echo('====================\n')

    contest_ballots = click.prompt('Enter number of contest ballots', type=click.IntRange(min=1))
    num_candidates = click.prompt('Enter number of candidates', type=click.IntRange(min=2))

    tally = {}
    while len(tally) == 0:
        running_total = 0
        for i in range(num_candidates):
            candidate = click.prompt('Enter candidate name', type=str)
            candidate_votes = click.prompt('Enter number of votes reported for {}'.format(candidate),
                                           type=click.IntRange(0, contest_ballots))
            running_total += candidate_votes
            if running_total > contest_ballots:
                input_warning('Exceeded total ballots cast in contest.')
                click.echo('Restarting tally process...\n')
                tally.clear()
                break
            tally[candidate] = candidate_votes

    num_winners = click.prompt('Enter number of winners', type=click.IntRange(1, num_candidates - 1))
    reported_winners = []
    candidates = list(tally.keys())
    for i in range(num_winners):
        winner = click.prompt('Enter winner name', type=click.Choice(candidates, case_sensitive=False))
        candidates.remove(winner)
        reported_winners.append(winner)

    contest_type_in = click.prompt('Select contest type', type=contest_types)
    contest_type = ContestType[contest_type_in]

    return Contest(contest_ballots, tally, num_winners, reported_winners, contest_type)


def input_election() -> Election:
    # Creates an election from user input
    click.echo('\nCreate a new Election')
    click.echo('=====================\n')

    name = click.prompt('Enter election name', type=str)
    total_ballots = click.prompt('Enter total ballots cast in election', type=click.IntRange(min=1))
    contests = {}

    while True:
        contest_name = click.prompt('\nEnter new contest name', type=str)
        contest = input_contest()
        contests[contest_name] = contest
        if not click.confirm('\nWould you like to enter another contest? '):
            break

    return Election(name, total_ballots, contests)


def input_warning(msg):
    click.echo('\nINVALID INPUT: ' + msg)
