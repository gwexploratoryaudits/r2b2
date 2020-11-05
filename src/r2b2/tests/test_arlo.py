import pytest

from r2b2.arlo import Audit

contest1 = {'contest_ballots': 100,
            'tally': {
                'A': 60,
                'B': 40
                },
            'num_winners': 1,
            'reported_winners': ['A'],
            'contest_type': 'MAJORITY'}
contest2 = {'contest_ballots': 100,
            'tally': {
                'C': 30,
                'D': 70
                },
            'num_winners': 1,
            'reported_winners': ['D'],
            'contest_type': 'MAJORITY'}
election = {'name': 'Example Election',
            'total_ballots': 200,
            'contests': {
                'contest1': contest1,
                'contest2': contest2
                }
            }


def test_create():
    audit = Audit('minerva', 0.1)
    assert audit.alpha == 0.1
    assert audit.election is None
    assert audit.minerva is None
    assert audit.contest is None
    assert audit.status == {}

def test_add_election_dict():
    audit = Audit('minerva', 0.1)
    audit.add_election(election)
    assert audit.election.name == 'Example Election'
    assert audit.election.total_ballots == 200
    assert len(audit.election.contests) == 2
    assert audit.contest == None
    assert audit.minerva == None
    assert audit.status == {}

def test_add_election_file():
    audit = Audit('minerva', 0.1)
    audit.add_election('src/r2b2/tests/data/arlo_election.json')
    assert audit.election.name == 'Example Election'
    assert audit.election.total_ballots == 200
    assert len(audit.election.contests) == 2
    assert audit.contest == None
    assert audit.minerva == None
    assert audit.status == {}

def test_load_contest():
    audit = Audit('minerva', 0.1)
    audit.add_election(election)
    audit.load_contest('contest1')
    assert audit.contest == 'contest1'
    assert audit.minerva is not None
    assert audit.minerva.contest.contest_ballots == 100
    assert audit.minerva.contest.tally == {'A': 60, 'B': 40}
    assert audit.minerva.contest.num_winners == 1
    assert audit.minerva.contest.reported_winners == ['A']
    assert audit.minerva.alpha == 0.1
    assert audit.minerva.max_fraction_to_draw == 1.0
    assert audit.contest in audit.status.keys()
    assert audit.status[audit.contest].risks == []
    assert audit.status[audit.contest].min_kmins == []

def test_find_round_size():
    # TODO
    pass

def test_set_observations():
    audit = Audit('minerva', 0.1)
    audit.add_election(election)
    audit.load_contest('contest1')
    audit.set_observations(0, 0, [6, 4])
    assert audit.minerva.rounds[0] == 10
    assert audit.minerva.sample_winner_ballots[0] == 6
    assert len(audit.status[audit.contest].risks) == 1
    assert len(audit.status[audit.contest].min_kmins) == 1

def test_execptions():
    # Create non-minerva Audit
    with pytest.raises(ValueError):
        audit = Audit('athena', 0.1)
    # Create minerva audit with invalid risk limit
    with pytest.raises(ValueError):
        audit = Audit('minerva', 5.0)
    audit = Audit('minerva', 0.1)
    # load contest beofre election is added
    with pytest.raises(Exception):
        audit.load_contest('contest1')
    # set observations before election is added
    with pytest.raises(Exception):
        audit.set_observations(0, 0, [1, 1])
    # add election with incorrect parameter
    with pytest.raises(TypeError):
        audit.add_election(5)
    audit.add_election(election)
    # add election after election is added
    with pytest.raises(Exception):
        audit.add_election(election)
    # set observations with election but no contest
    with pytest.raises(Exception):
        audit.set_observations(0, 0, [1, 1])
    audit.load_contest('contest1')
    # load contest after contest is loaded
    with pytest.raises(Exception):
        audit.load_contest('contest2')
    # set observations with incorrect rounds
    with pytest.raises(Exception):
        audit.set_observations(0, 0, [1])
    with pytest.raises(Exception):
        audit.set_observations(0, 0, [1, 1, 1])
