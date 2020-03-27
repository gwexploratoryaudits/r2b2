import pytest

import r2b2.tests.util as util
from r2b2.election import Election


def test_simple_election():
    contests = []
    for i in range(10):
        contests.append(util.generate_contest(100))
    simple_election = Election('test_simple_election', 1000, contests)
    assert simple_election.name == 'test_simple_election'
    assert simple_election.total_ballots == 1000
    assert simple_election.contests is contests


def test_repr():
    contests = []
    for i in range(10):
        contests.append(util.generate_contest(100))
    simple_election1 = Election('Example Election', 100, contests)
    simple_election2 = Election('Example Election', 100, contests)
    assert repr(simple_election1) == repr(simple_election2)


def test_str():
    contests = []
    for i in range(10):
        contests.append(util.generate_contest(100))
    simple_election = Election('Example Election', 100, contests)
    election_str = 'Election\n--------\nName: Example Election\n'
    election_str += 'Total Ballots: 100\nList of Contests:\n'
    for contest in contests:
        election_str += str(contest)
    assert str(simple_election) == election_str


def test_initialization_errors():
    name = 'BadElection'
    contests = []
    for i in range(10):
        contests.append(util.generate_contest(100))
    single_contest = util.generate_contest(100)

    # name TypeError
    with pytest.raises(TypeError):
        Election(123, 100, contests)
    with pytest.raises(TypeError):
        Election(False, 100, contests)
    # total_ballots TypeError
    with pytest.raises(TypeError):
        Election(name, 12.5, contests)
    with pytest.raises(TypeError):
        Election(name, False, contests)
    with pytest.raises(TypeError):
        Election(name, '1200', contests)
    # total_ballots ValueError
    with pytest.raises(ValueError):
        Election(name, 0, contests)
    # contests TypeError
    with pytest.raises(TypeError):
        Election(name, 100, 12)
    with pytest.raises(TypeError):
        Election(name, 100, True)
    with pytest.raises(TypeError):
        Election(name, 100, single_contest)
    with pytest.raises(TypeError):
        Election(name, 100, None)
    contests.append('120')
    with pytest.raises(TypeError):
        Election(name, 100, contests)
