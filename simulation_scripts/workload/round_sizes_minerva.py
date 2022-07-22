"""
Script to run the simulations presented in the workload/multiple rounds section of the Providence paper.

Simulations assume that the announced results are correct (ie draws from the distribution specified by the reported margin. 
Contest: 2020 US Presidential contest, Pennsylvania state-wide
Alpha: 10\%
"""

import json
import logging

from r2b2.simulation.minerva import MinervaMultiRoundStoppingProb as MMRSP
from r2b2.minerva import Minerva
from r2b2.tests.util import parse_election
from r2b2.simulator import DBInterface

from pymongo import MongoClient

#from txtme import txtme

election = parse_election('data/2020_presidential/2020_presidential.json')

def state_trial(state, alpha, sample_size, sprob):
    # connect to database
    db = MongoClient(host='localhost', port=27017, username='sarah', password='haras')['r2b2']

    # find correct audit entry in db
    query = {'audit_type': 'minerva', 'alpha': .1}
    audit_id = db.audits.find_one(query)['_id']

    # find contest entry in db
    contest_obj = election.contests[state]
    query = {
        'contest_ballots': contest_obj.contest_ballots,
        'tally': contest_obj.tally,
        'num_winners': contest_obj.num_winners,
        'reported_winners': contest_obj.reported_winners,
        'description': '2020 Presidential'
    }
    contest_id = db.contests.find_one(query)['_id']

    # find simulation entry in db
    query = {
        'reported': contest_id, 
        'underlying': 'reported', 
        'audit': audit_id, 
        'invalid_ballots': True, 
        'first_round_sprob': sprob,
        'description' : 'Prov paper: Minerva workload',
        'max_rounds': 100
    }
    sim = db.simulations.find_one(query)

    # count number of trials already done
    if sim is None:
        num_trials = 0
    else:
        if 'analysis' in sim.keys() and 'remaining_by_round' in sim['analysis'].keys():
            num_trials = sim['analysis']['remaining_by_round'][0]
        else:
            query = {'simulation' : sim['_id']}
            num_trials = db.trials.count_documents(query)

    # Create simulation object to run more trials
    sim_obj = MMRSP(alpha,
               election.contests[state],
               max_rounds=100,
               sample_size=sample_size,
               sample_mult=1,
               first_round_sprob=sprob,
               sim_args={'description': 'Prov paper: Minerva workload'},
               user='sarah',
               pwd='haras',
               reported_args={
                   'name': state,
                   'description': '2020 Presidential'
               })
  
    # Run simulation
    total_trials = 10000
    trials_left = total_trials - num_trials
    print('Running '+str(trials_left)+' trials...')
    sim_obj.run(trials_left)
    if trials_left > 0:
        return sim_obj.analyze()
    else:
        return sim['analysis']['sprob']
 
if __name__ == '__main__':
    #contest = 'Pennsylvania'
    contest = 'Michigan'
    #contest = 'California'
    print('Simulations for '+contest)
    winner_tally = election.contests[contest].tally[election.contests[contest].reported_winners[0]]
    tally = sum(election.contests[contest].tally.values())
    loser_tally = tally - winner_tally
    margin = (winner_tally - loser_tally) / tally
    sprobs = [.95, .9, .85, .8, .75, .7, .65, .6, .55, .5, .45, .4, .35, .3, .25, .2, .15, .1, .05]
    print(sprobs)
    for sprob in sprobs:
        #print('sprob='+str(sprob))
        tmpaudit = Minerva(0.1, 1.0, election.contests[contest])
        sample_size = tmpaudit.next_sample_size(sprob)
        #print('for sprob '+str(sprob)+' use first round size '+str(sample_size))
        print(str(sample_size)+',')
        #computed_risk = state_trial(contest, 0.1, sample_size, sprob)
        #logging.info('{}: {}'.format(contest, computed_risk))
