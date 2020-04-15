import pytest
import json

import r2b2.tests.util as util
from r2b2.brla import BayesianRLA as BRLA
from r2b2.contest import Contest
from r2b2.contest import ContestType

default_contest = util.generate_contest(100)


def test_simple_brla():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    assert simplebrla.alpha == 0.1
    assert simplebrla.beta == 0.0
    assert simplebrla.max_fraction_to_draw == 0.2
    assert not simplebrla.replacement
    assert simplebrla.contest is default_contest
    simplebrla.rounds.append(20)
    assert simplebrla.stopping_condition(20)
    assert not simplebrla.stopping_condition(0)
    test_min_winner_ballots = simplebrla.next_min_winner_ballots(20)
    assert test_min_winner_ballots >= 10
    assert test_min_winner_ballots <= 20
    bulk_min_winner_ballots = simplebrla.compute_all_min_winner_ballots()
    assert len(bulk_min_winner_ballots) == (20 - simplebrla.min_sample_size) + 1


def test_exceptions():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    with pytest.raises(Exception):
        simplebrla.stopping_condition(10)
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([0, 1])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([10, 5])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([100])
    with pytest.raises(ValueError):
        simplebrla.compute_all_min_winner_ballots(0)
    with pytest.raises(ValueError):
        simplebrla.compute_all_min_winner_ballots(1000)


def test_paper_data():
    """Test brla using data from BRLA paper Table 3."""
    with open('src/r2b2/tests/brla_test_data.json', 'r') as json_file:
        data = json.load(json_file)

    rounds = data['rounds']
    contest = Contest(100000, {'A':60000, 'B':40000}, 1, ['A'], ContestType.PLURALITY)
    
    for test in data['test_cases']:
        audit = BRLA(data['test_cases'][test]['risk'], 1.0, contest)
        kmins = audit.compute_min_winner_ballots(rounds)
        assert kmins == data['test_cases'][test]['kmins']
