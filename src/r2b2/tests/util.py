import json
import math
from random import randint

from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.election import Election


def generate_contest(max_size):
    """Generate a Contest with random data. For testing purposes only.

    Note:
        Currently this only generates 2 candidate Plurality contests with 1 winner.
    """
    contest_ballots = randint(1, max_size)
    win_tally = randint(math.ceil(contest_ballots / 2), contest_ballots)
    tally = {'a': win_tally, 'b': contest_ballots - win_tally}

    return Contest(contest_ballots, tally, 1, ['a'], ContestType.PLURALITY)


def generate_election(max_size, max_contests=None):
    """Generate an Election with random data. For testing purposes only."""
    name = 'TestElection' + str(randint(1, 100))
    total_ballots = randint(1, max_size)
    if max_contests is None:
        max_contests = 20
    num_contests = randint(1, max_contests)
    contests = list()
    for i in range(num_contests):
        contests.append(generate_contest(total_ballots))

    return Election(name, total_ballots, contests)


def parse_contest_list(json_file):
    """Parse a list of Contests from a JSON file.

    Note:
        Template for Contest format in JSON in contest_template.json
    """
    with open(json_file, 'r') as json_data:
        data = json.load(json_data)

    contests = []

    for contest in data:
        contest_ballots = data[contest]['contest_ballots']
        tally = data[contest]['tally']
        num_winners = data[contest]['num_winners']
        reported_winners = data[contest]['reported_winners']
        contest_type = ContestType[data[contest]['contest_type']]
        contests.append(
            Contest(contest_ballots, tally, num_winners, reported_winners,
                    contest_type))

    return contests


def parse_election(json_file):
    """Parse an Eleciton from a JSON file.

    Note:
        Templace for Election JSON format in election_template.json
    """
    with open(json_file, 'r') as json_data:
        data = json.load(json_data)

    name = data['name']
    total_ballots = data['total_ballots']
    contests = []

    for contest in data['contests']:
        contest_ballots = data['contests'][contest]['contest_ballots']
        tally = data['contests'][contest]['tally']
        num_winners = data['contests'][contest]['num_winners']
        reported_winners = data['contests'][contest]['reported_winners']
        contest_type = ContestType[data['contests'][contest]['contest_type']]
        contests.append(
            Contest(contest_ballots, tally, num_winners, reported_winners,
                    contest_type))

    return Election(name, total_ballots, contests)
