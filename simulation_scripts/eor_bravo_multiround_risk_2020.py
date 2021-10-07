"""
Script to run simulations of a EOR_BRAVO audit over a maximum of 5 rounds,
where each round size is estimated to achieve a 90% probability of stopping.
Underlying distribution is a tie.
"""

import json
import logging

from r2b2.simulation.eor_bravo import EOR_BRAVOMultiRoundRisk as EBMRR
from r2b2.tests.util import parse_election
from r2b2.simulator import DBInterface

from pymongo import MongoClient

#from txtme import txtme

election = parse_election('data/2020_presidential/2020_presidential.json')


def state_trial(state, alpha):
    # Find the number of trials so we can keep all even
    db = MongoClient(host='localhost', port=27017, username='writer', password='icanwrite')['r2b2']
    query = {'audit_type': 'eor_bravo', 'alpha': .1}
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
        'description' : 'Multiround EOR_BRAVO (90%)',
        'max_rounds': 5
    }
    sim = db.simulations.find_one(query)
    if sim is None:
        num_trials = 0
    else:
        if 'analysis' in sim.keys() and 'remaining_by_round' in sim['analysis'].keys():
            num_trials = sim['analysis']['remaining_by_round'][0]
        else:
            query = {'simulation' : sim['_id']}
            num_trials = db.trials.count_documents(query)

    # Create simulation
    sim_obj = EBMRR(alpha,
               election.contests[state],
               max_rounds=5,
               sample_sprob=.9,
               sim_args={'description': 'Multiround EOR_BRAVO (90%)'},
               user='writer',
               pwd='icanwrite',
               reported_args={
                   'name': state,
                   'description': '2020 Presidential'
               })
  
    # Run simulation
    trials_left = 10000 - num_trials
    #txtme('Running {} more risk trials for {}'.format(trials_left, state))
    #print('running',trials_left,'trials for',state)
    sim_obj.run(trials_left)
    #txtme('Ran {} more risk trials for {}'.format(trials_left, state))
    if trials_left > 0:
        return sim_obj.analyze()
    else:
        return sim['analysis']['risk']

if __name__ == '__main__':
    for contest in election.contests.keys():
        winner_tally = election.contests[contest].tally[election.contests[contest].reported_winners[0]]
        tally = sum(election.contests[contest].tally.values())
        loser_tally = tally - winner_tally
        margin = (winner_tally - loser_tally) / tally
        if margin < 0.05:
            print('Skipping',contest,'with margin',round(margin,5))
            continue
        computed_risk = state_trial(contest, 0.1)
        logging.info('{}: {}'.format(contest, computed_risk))
    #txtme('Done with current risk simulations')
