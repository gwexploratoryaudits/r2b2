"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mr2b2` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``r2b2.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``r2b2.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import argparse
import math

from r2b2.audit import Audit
from r2b2.brla import BayesianRLA as BRLA
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.tests import util

parser = argparse.ArgumentParser(description='Begin the R2B2 auditing tool.')
parser.add_argument('-i',
                    '--interactive',
                    help='Use interactive R2B2 auditing tool.',
                    dest='interactive',
                    action='store_true',
                    default=False)
parser.add_argument('-e',
                    '--election_mode',
                    help='Use election mode, rather than single-contest mode.',
                    dest='election_mode',
                    action='store_true',
                    default=False)
parser.add_argument('--election_file',
                    metavar='ELECTION FILE',
                    help='Create Election object from JSON file.',
                    dest='election_file',
                    default=None)
parser.add_argument('--contest_file',
                    metavar='CONTEST FILE',
                    help='Create Contest object from JSON file.',
                    dest='contest_file',
                    default=None)
parser.add_argument('-a',
                    '--audit-type',
                    metavar='AUDIT TYPE',
                    help='Audit type to use on Election/Contest audits.',
                    dest='audit_type',
                    choices=['brla'],
                    default=None)
parser.add_argument('-r',
                    '--risk-limit',
                    metavar='RISK LIMIT',
                    help='Risk limit (alpha) of the audit.\n \
                          Value should be a float between 0.0 and 1.0',
                    dest='alpha',
                    default=None,
                    type=float)
parser.add_argument('-m',
                    '--max-fraction-to-draw',
                    metavar='MAX FRACTION TO DRAW',
                    help='Maximum fraction of ballots to draw during audit.',
                    dest='max_fraction_to_draw',
                    default=None,
                    type=float)
parser.add_argument('-l',
                    '--round-list',
                    metavar='ROUND LIST',
                    help='Provide a list of round sizes for bulk computation.',
                    dest='rounds',
                    default=None,
                    nargs='+',
                    type=int)
parser.add_argument('-f',
                    '--full-audit-limit',
                    metavar='FULL AUDIT MAXIMUM SIZE',
                    help='Set maximum size of full audit in bulk mode.',
                    dest='max_size',
                    type=int,
                    default=None)
parser.add_argument('-o',
                    '--output',
                    metavar='OUTPUT FILE',
                    help='Write output to a given file in bulk mode.',
                    dest='output',
                    default=None)
parser.add_argument('-v',
                    '--verbose',
                    help='Get verbose output. Provides additional audit statistics in interactive.',
                    dest='verbose',
                    action='store_true',
                    default=False)


def main(args=None):
    args = parser.parse_args(args=args)
    if args.interactive:
        print('Beginning interactive R2B2 auditing tool...\n\n')
        if args.election_mode:
            print('Election mode is currently unavailable.')
            # TODO: implement auditing an election
            return
        else:
            if args.contest_file is not None:
                contest = util.parse_contest(str(args.contest_file))
                print(contest)
            else:
                contest = input_contest()

            audit = input_audit(contest, args.alpha, args.max_fraction_to_draw, args.audit_type)
            audit.run(args.verbose)
    elif args.election_mode:
        print('Bulk Election mode is currently unavailable.')
        # TODO: implement election auditing
        return
    else:
        # Get contest from contest file
        if args.contest_file is None:
            raise Exception('Contest file must be provided in bulk mode.')
        contest = util.parse_contest(str(args.contest_file))
        # Ensure all Audit parameters are given
        if args.audit_type is None:
            raise Exception('Audit type must be provided in bulk mode.')
        if args.max_fraction_to_draw is None:
            raise Exception('Max fraction to draw must be provided in bulk mode.')
        if args.alpha is None:
            raise Exception('Risk-limit must be provided in bulk mode.')
        # Create audit based on type
        # If any additional args are needed, parse and verify here
        if args.audit_type == 'brla':
            audit = BRLA(args.alpha, args.max_fraction_to_draw, contest)
        else:
            raise Exception('Audit type must be a valid choice.')
        # Determine if mode is rounds, list, or full list
        # Create formatted output
        out = '\n{:^20}|{:^20}\n'.format('Round Sizes', 'Stopping Sizes')
        out += '--------------------|--------------------\n'
        if args.rounds is not None:
            kmins = audit.compute_min_winner_ballots(args.rounds)
            for i in range(len(kmins)):
                out += '{:^20}|{:^20}\n'.format(args.rounds[i], kmins[i])
        elif args.max_size is not None:
            kmins = audit.compute_all_min_winner_ballots(args.max_size)
            for r in range(audit.min_sample_size, args.max_size + 1):
                out += '{:^20}|{:^20}\n'.format(r, kmins[r - audit.min_sample_size])
        else:
            max_size = math.ceil(audit.max_fraction_to_draw * audit.contest.contest_ballots)
            kmins = audit.compute_all_min_winner_ballots()
            for r in range(audit.min_sample_size, max_size + 1):
                out += '{:^20}|{:^20}\n'.format(r, kmins[r - audit.min_sample_size])
        # Either print output or write to given file
        if args.output is not None:
            with open(args.output, 'w') as out_file:
                out_file.write(out)
                out_file.close()
        else:
            print(out)


def input_audit(contest: Contest, alpha: float = None, max_fraction_to_draw: float = None, audit_type: str = None) -> Audit:
    """Create an audit from user-input."""
    print('\nCreate a new Audit')
    print('==================\n')

    if alpha is None:
        alpha = float(input('Enter the desired risk limit: '))
    while alpha <= 0.0 or alpha >= 1.0:
        print('Invalid Input: Risk limit must be a float between 0 and 1.')
        alpha = float(input('Enter the desired risk limit: '))

    if max_fraction_to_draw is None:
        max_fraction_to_draw = float(input('Enter the maximum fraction of contest ballots you are willing to draw: '))
    while max_fraction_to_draw <= 0.0 or max_fraction_to_draw > 1.0:
        print('Invalid Input: Max Fraction must be between 0 and 1.')
        max_fraction_to_draw = float(input('Enter the maximum fraction of contest ballots you are willing to draw: '))

    if audit_type is None:
        print('\nAudit Types')
        print('-----------')
        print('1 - Bayesian RLA without replacement')
        print()
        audit_type_in = int(input('Select an audit type: '))
        while audit_type_in < 1 or audit_type_in > 1:
            print('Invalid selection!')
            audit_type_in = int(input('Select an audit type: '))
        if audit_type_in == 1:
            audit_type = 'brla'
        # TODO: add additional audit type selections

    if audit_type == 'brla':
        return BRLA(alpha, max_fraction_to_draw, contest)
    # TODO: add creation for other types of audits.
    return None


def input_contest() -> Contest:
    """Creates a contest from user-input."""

    print('\nCreate a new Contest')
    print('====================\n')

    contest_ballots = int(input('Enter number of contest ballots: '))
    while contest_ballots < 1:
        print('Invalid Input!')
        contest_ballots = int(input('Enter number of contest ballots: '))

    num_candidates = int(input('Enter number of candidates: '))
    while num_candidates < 2:
        print('Invalid Input!')
        num_candidates = int(input('Enter number of candidates: '))

    tally = {}
    while len(tally) == 0:
        running_total = 0
        for i in range(num_candidates):
            candidate = input('Enter candidate name: ')
            candidate_votes = int(input('Enter number of votes reported for candidate: '))
            while candidate_votes < 0:
                print('Invalid Input: Votes must be non-negative')
                candidate_votes = int(input('Enter number of votes reported for candidate: '))
            running_total += candidate_votes
            if running_total > contest_ballots:
                print('Invalid Input: Exceeded total ballots cast in contest.')
                print('Restarting tally process...')
                tally.clear()
                break
            tally[candidate] = candidate_votes

    num_winners = int(input('Enter number of winners: '))
    while num_winners >= num_candidates:
        print('Invalid Input!')
        num_winners = int(input('Enter number of winners: '))

    reported_winners = []
    candidates = list(tally.keys())
    for i in range(num_winners):
        winner = input('Enter winner name: ')
        while winner not in candidates or winner in reported_winners:
            print('Invalid Input: Must be a candidate who is not already a reported winner.')
            winner = input('Enter winner name:')
        reported_winners.append(winner)

    print('\nContest Types')
    print('-------------')
    print('0 - PLURALITY')
    print('1 - MAJORITY')
    print()
    # TODO: Additional contest types should be added here once added in contest.py
    contest_type_in = int(input('Select contest type from above: '))
    while contest_type_in < 0 or contest_type_in > 1:
        print('Invalid Input: Selection must be in menu above.')
        contest_type_in = int(input('Select contest type from above: '))
    contest_type = ContestType(contest_type_in)

    return Contest(contest_ballots, tally, num_winners, reported_winners, contest_type)
