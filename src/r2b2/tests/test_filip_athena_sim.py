from r2b2.simulation.filip_athena import FZMinervaOneRoundRisk as FZMR
from r2b2.tests.util import parse_election


election_file = 'src/r2b2/tests/data/election_template.json'
contest_name = 'contest1'
election = parse_election(election_file)
contest = election.contests[contest_name]

def test_creation():
    sim = FZMR(0.1, contest, 10, election_file, contest_name, db_mode=False)
    assert(len(sim.trials) == 0)
    assert(sim.alpha == 0.1)
    assert(sim.sample_size == 10)
    assert(sim.audit_type == 'fz_minerva')
    assert(sim.underlying == 'tie')
    assert(sim.db is None)
    assert(sim.audit_id is None)
    assert(sim.reported_id is None)
    assert(sim.sim_id is None)

def test_one_trial():
    sim = FZMR(0.1, contest, 10, election_file, contest_name, db_mode=False)
    sim.run(1)
    assert(len(sim.trials) == 1)
    keys = list(sim.trials[0].keys())
    expected_keys = ['simulation', 'seed', 'stop', 'p_value', 'sample_size', 'relevant_sample_size', 'winner_ballots']
    assert(keys == expected_keys)
