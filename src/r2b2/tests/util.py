from random import randint

from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.election import Election


def generate_contest(max_size):
    """Generate a Contest with random data. For testing prposes only.

    Note:
        Currently this only generates 2 candidate Pluraity contests with 1 winner.
    """
    contest_ballots = randint(1, max_size)
    win_tally = randint(contest_ballots // 2, contest_ballots)
    tally = {'a': win_tally, 'b': contest_ballots - win_tally}

    return Contest(contest_ballots, tally, 1, ['a'], ContestType.PLURALITY)


def generate_election(max_size, max_contests=None):
    name = 'TestElection' + str(randint(1, 100))
    total_ballots = randint(1, max_size)
    if max_contests is None:
        max_contests = 20
    num_contests = randint(1, max_contests)
    contests = list()
    for i in range(num_contests):
        contests.append(generate_contest(total_ballots))

    return Election(name, total_ballots, contests)
