"""
Module that contains the command line app.

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

import click

from r2b2.audit import Audit
from r2b2.brla import BayesianRLA as BRLA
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.tests import util


# Class for parsing space separated list of integers from command line
class IntList(click.ParamType):
    name = 'integer list'

    def convert(self, value, param, ctx):
        try:
            str_list = value.split(' ')
            return [int(i) for i in str_list]
        except TypeError:
            self.fail('Expected space separatedlist of integers')


INT_LIST = IntList()

# Audit type choices
# TODO: add new audit types when they become available
audit_types = click.Choice(['brla'], case_sensitive=False)
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
@click.option('--election-file', type=click.File(), help='Pass election data as JSON file.')  # TODO: provide format
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
@click.option('-v',
              '--verbose',
              default=False,
              is_flag=True,
              flag_value=True,
              show_default=False,
              help='Provides risk and stopping probability schedule of previous rounds, minimum and  maximum sample size.')
def interactive(election_mode, election_file, contest_file, audit_type, risk_limit, max_fraction_to_draw, verbose):
    """Executes an audit round by round.

    \b
    In interactive mode users will be prompted for:
        - Contest results (unless a contest file is provided)
        - Audit type (if not provided with -a)
        - Risk Limit (if not provided with -r)
        - Maximum fraction of contest ballots to draw (if not given with -m)
        - Each round size
    """

    if election_mode:
        click.echo('Election mode is currently unavailable.')
        # TODO: Implement interactive election mode
        return

    # Check contest file if provided, otherwise request contest input
    if contest_file is not None:
        contest = util.parse_contest(str(contest_file))
    else:
        contest = input_contest()

    # Confirm contest, if incorrect get new input
    click.echo('\n')
    click.echo(contest)
    while not click.confirm('\nUse the above contest data?'):
        contest = input_contest()
        click.echo(contest)

    # Create audit from prompted input
    audit = input_audit(contest, risk_limit, max_fraction_to_draw, audit_type)
    click.echo(audit)
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

    \b
    For bulk execution, the user provides the following arguments:
    - AUDIT_TYPE            Which type of audit to use to generate stopping sizes
    - RISK_LIMIT            Risk limit (alpha) provided to audit.
    - MAX_FRACTION_TO_DRAW  Maximum fraction of contest ballots that could be drawn during the audit.
                            This sets the default maximum size for the ballot by ballot result.
    - CONTEST_FILE          Contest data as a JSON file.
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
        kmins = audit.compute_min_winner_ballots(round_list)
        for i in range(len(kmins)):
            out += '{:^20}|{:^20}\n'.format(round_list[i], kmins[i])
    elif full_audit_limit is not None:
        kmins = audit.compute_all_min_winner_ballots(full_audit_limit)
        for r in range(audit.min_sample_size, full_audit_limit + 1):
            out += '{:^20}|{:^20}\n'.format(r, kmins[r - audit.min_sample_size])
    else:
        kmins = audit.compute_all_min_winner_ballots()
        for r in range(audit.min_sample_size, math.ceil(max_fraction_to_draw * contest.contest_ballots) + 1):
            out += '{:^20}|{:^20}\n'.format(r, kmins[r - audit.min_sample_size])

    # TODO: what does verbose mean for bulk?

    # Write or print output
    if output is not None:
        output.write(out)
    else:
        click.echo(out)


def input_audit(contest: Contest, alpha: float = None, max_fraction_to_draw: float = None, audit_type: str = None) -> Audit:
    """Create an audit from user-input."""
    click.echo('\nCreate a new Audit')
    click.echo('==================\n')

    if alpha is None:
        alpha = click.prompt('Enter the desired risk limit', type=click.FloatRange(0.0, 1.0))
    if max_fraction_to_draw is None:
        max_fraction_to_draw = click.prompt('Enter the maximum fraction of contest ballots to draw', type=click.FloatRange(0.0, 1.0))
    if audit_type is None:
        audit_type = click.prompt('Select an audit type', type=audit_types)

    if audit_type == 'brla':
        return BRLA(alpha, max_fraction_to_draw, contest)
    # TODO: add creation for other types of audits.
    return None


def input_contest() -> Contest:
    """Creates a contest from user-input."""

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


def input_warning(msg):
    click.echo('\nINVALID INPUT: ' + msg)
