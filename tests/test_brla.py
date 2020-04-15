import json

from r2b2.brla import BayesianRLA as BRLA
from r2b2.contest import Contest
from r2b2.contest import ContestType


def test_paper_data():
    """Test brla using data from BRLA paper Table 3."""
    with open('tests/data/brla_test_data.json', 'r') as json_file:
        data = json.load(json_file)

    rounds = data['rounds']
    contest = Contest(100000, {
        'A': 60000,
        'B': 40000
    }, 1, ['A'], ContestType.PLURALITY)

    for test in data['test_cases']:
        audit = BRLA(data['test_cases'][test]['risk'], 1.0, contest)
        kmins = audit.compute_min_winner_ballots(rounds)
        assert kmins == data['test_cases'][test]['kmins']
