"""
Script to run the simulations presented in the workload/multiple rounds section of the Providence paper.

Simulations assume that the announced results are correct (ie draws from the distribution specified by the reported margin. 
Contest: 2020 US Presidential contest, Pennsylvania state-wide
Alpha: 10\%
"""

import json
import logging

from r2b2.simulation.eor_bravo import EOR_BRAVOMultiRoundStoppingProb as MMRSP
from r2b2.tests.util import parse_election
from r2b2.simulator import DBInterface
from r2b2.contest import Contest
from r2b2.contest import ContestType

from pymongo import MongoClient

#from txtme import txtme


def state_trial(state, alpha, sprob, contest_name, per_precinct_ballots):
    # to avoid the effort of renaming, the first intput called state is the contest objhect
    contest= state
    contest_obj=state
    # Find the number of trials so we can keep all even
    db = MongoClient(host='localhost', port=27017, username='writer', password='icanwrite')['r2b2']
    query = {'audit_type': 'eor_bravo', 'alpha': .1}
    audit_id = db.audits.find_one(query)['_id']
    #contest_obj = election.contests[state]
    contest_obj = state# for this script, state argument was already a contest ob
    query = {
        'contest_ballots': contest_obj.contest_ballots,
        'tally': contest_obj.tally,
        'num_winners': contest_obj.num_winners,
        'reported_winners': contest_obj.reported_winners,
        'description': '2020 Presidential'
    }
    #'name': state,
    #print(query)


    dbinterface = DBInterface(host='localhost', port=27017, name='r2b2', user='writer', pwd='icanwrite')
    contest_id = dbinterface.contest_lookup(contest)
    #contest_id = db.contests.find_one(query)['_id']
    query = {
        'reported': contest_id, 
        'underlying': 'reported', 
        'audit': audit_id, 
        'invalid_ballots': True, 
        'description' : 'Per-precinct Providence',
        'max_rounds': 100
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
               contest,
               #per_precinct_ballots,
               max_rounds=100,
               sample_sprob=sprob,
               sim_args={'description': 'Pre-precinct Providence'},
               user='writer',
               pwd='icanwrite',
               reported_args={
                   'name': contest_name,
                   'description': '2020 Presidential'
               })
  
    # Run simulation
    total_trials = 100
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
    # manually construct contest object from known values
    contest_name = 'Virginia 2016 presidential contest'
    tally = {'Hillary R. Clinton': 1981473, 'Donald J. Trump': 1769443, 'Gary Johnson': 118274, 'Evan McMullin':54054, 'Jill Stein':27638, 'All Others':33749}
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
    with open('bals.json') as f:
        per_precinct_ballots = json.load(f)["bals"]
    print('Simulations for '+contest_name)
    winner_tally = winner_votes
    loser_tally = loser_votes
    for sprob in [.95, .85, .75, .65, .55, .45, .35, .25, .15, .05]:
        print('sprob='+str(sprob))
        computed_risk = state_trial(contest, 0.1, sprob, contest_name, per_precinct_ballots)
        logging.info('{}: {}'.format(contest, computed_risk))
