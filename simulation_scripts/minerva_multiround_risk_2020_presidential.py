import json
import logging

from r2b2.simulation.minerva import MinervaMultiRoundRisk as MMRR
from r2b2.tests.util import parse_election
from r2b2.simulator import DBInterface

from pymongo import MongoClient

election = parse_election('data/2020_presidential/2020_presidential.json')
sample_size_file = 'data/2020_presidential/2020_presidential_sample_sizes.json'


def state_trial(state, alpha, sample_size):
    # Find the number of trials so we can keep all even
    db = MongoClient(host='localhost', port=27017, username='', password='')['r2b2']
    query = {'audit_type': 'minerva', 'alpha': .1}
    audit_id = db.audits.find_one(query)['_id']
    contest_obj = election.contests[state]
    query = {
        'contest_ballots': contest_obj.contest_ballots,
        'tally': contest_obj.tally,
        'num_winners': contest_obj.num_winners,
        'reported_winners': contest_obj.reported_winners,
        'name': state,
        'description': '2020 Presidential'
    }
    contest_id = db.contests.find_one(query)['_id']
    query = {
        'reported': contest_id, 
        'underlying': 'tie', 
        'audit': audit_id, 
        'invalid_ballots': True, 
        'description' : 'Multi round Minerva (90% then 1.5x)',
        'sample_mult':1.5,
        'max_rounds': 5
    }
    sim = db.simulations.find_one(query)
    query = {'simulation' : sim['_id']}
    num_trials = db.trials.count_documents(query)

    # Create simulation
    sim = MMRR(alpha,
               election.contests[state],
               sample_size,
               sample_mult=1.5,
               max_rounds=5,
               sim_args={'description': 'Multi round Minerva (90% then 1.5x)'},
               user='',
               pwd='',
               reported_args={
                   'name': state,
                   'description': '2020 Presidential'
               })
  
    # Run simulation
    trials_left = 100000 - num_trials
    print('running',trials_left,'trials for',state)
    sim.run(trials_left)
    return sim.analyze()

if __name__ == '__main__':
    with open(sample_size_file, 'r') as fd:
        sample_sizes = json.load(fd)
        for contest in election.contests.keys():
            winner_tally = election.contests[contest].tally[election.contests[contest].reported_winners[0]]
            tally = sum(election.contests[contest].tally.values())
            loser_tally = tally - winner_tally
            margin = (winner_tally - loser_tally) / tally
            if margin < 0.05:
                print('Skipping',contest,'with margin',round(margin,5))
                continue
            sample_size = sample_sizes[contest]['Minerva_pv_scaled'][0]
            computed_risk = state_trial(contest, 0.1, sample_size)
            logging.info('{}: {}'.format(contest, computed_risk))
