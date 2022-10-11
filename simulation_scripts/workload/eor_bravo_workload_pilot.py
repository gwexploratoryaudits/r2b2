"""
Script to run the simulations presented in the workload/multiple rounds section of the Providence paper.

Simulations assume that the announced results are correct (ie draws from the distribution specified by the reported margin. 
Contest: pilot audit febraury 2020 in providence, rhode island
Alpha: 10\%
"""

import json
import logging

from r2b2.simulation.eor_bravo import EOR_BRAVOMultiRoundStoppingProb as MMRSP
from r2b2.simulator import DBInterface
from r2b2.contest import Contest
from r2b2.contest import ContestType

from pymongo import MongoClient

#from txtme import txtme


def state_trial(contest, alpha, sprob):
    # Find the number of trials so we can keep all even
    db_interface = DBInterface(host='localhost', port=27017, name='r2b2', user='writer', pwd='icanwrite')
    db = MongoClient(host='localhost', port=27017, username='writer', password='icanwrite')['r2b2']
    query = {'audit_type': 'eor_bravo', 'alpha': .1}
    audit_id = db.audits.find_one(query)['_id']
    contest_obj = contest
    query = {
        'contest_ballots': contest_obj.contest_ballots,
        'tally': contest_obj.tally,
        'num_winners': contest_obj.num_winners,
        'reported_winners': contest_obj.reported_winners,
        'description': '2020 Presidential'
    }
    #'name': state,
    #print(query)
    #contest_id = db.contests.find_one(query)['_id']
    contest_id = db_interface.contest_lookup(contest)
    query = {
        'reported': contest_id, 
        'underlying': 'reported', 
        'audit': audit_id, 
        'invalid_ballots': True, 
        'description' : 'eor bravo pilot workload',
        'max_rounds': 1000
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
    sim_obj = MMRSP(alpha,
               contest_obj,
               max_rounds=1000,
               sample_sprob=sprob,
               sim_args={'description': 'eor bravo pilot workload'},
               user='writer',
               pwd='icanwrite',
               reported_args={
                   'name': 'Pilot',
                   'description': '2020 Presidential'
               })
  
    # Run simulation
    total_trials = 1000
    trials_left = total_trials - num_trials
    print('Running '+str(trials_left)+' trials...')
    #txtme('Running {} sprob trials for {}'.format(trials_left, state))
    sim_obj.run(trials_left)
    #txtme('Ran {} more sprob trials for {}'.format(trials_left, state))
    if trials_left > 0:
        return sim_obj.analyze()
    else:
        return sim['analysis']['sprob']
 
if __name__ == '__main__':
    contest_name = "\nSchool Construction and Renovation Projects"
    tally = {'Approve' : 2391, 'Reject' : 1414}
    reported_winner = max(tally, key=tally.get)
    winner_votes = tally[reported_winner]
    total_relevant = sum(tally.values())
    loser_votes = total_relevant - winner_votes
    margin = (winner_votes / total_relevant) - (loser_votes / total_relevant)
    # Make the contest object
    contest = Contest(total_relevant,
                                tally,
                                num_winners=1,
                                reported_winners=[reported_winner],
                                contest_type=ContestType.PLURALITY)
    print('Simulations for '+contest_name)
    for sprob in [.95, .85, .75, .65, .55, .45, .35, .25, .15, .05]:
        print('sprob='+str(sprob))
        computed_risk = state_trial(contest, 0.1, sprob)
        logging.info('{}: {}'.format(contest, computed_risk))
