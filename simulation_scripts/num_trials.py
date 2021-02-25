"""
Script to get the number of trials per state for a given simulation type.
"""

from pymongo import MongoClient
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

db = MongoClient(host='localhost', port=27017, username='', password='')['r2b2']
query = {'audit_type': 'minerva', 'alpha': .1}
audit = db.audits.find_one(query)
audit_id = audit['_id']

for contest in election.contests.keys():
    winner_tally = election.contests[contest].tally[election.contests[contest].reported_winners[0]]
    tally = sum(election.contests[contest].tally.values())
    loser_tally = tally - winner_tally
    margin = (winner_tally - loser_tally) / tally
    if margin < 0.05:
        print('Skipping',contest,'with margin',round(margin,5))
        continue
    #if not(contest=='Wyoming'):
    #    continue
    contest_obj = election.contests[contest]
    query = {
        'contest_ballots': contest_obj.contest_ballots,
        'tally': contest_obj.tally,
        'num_winners': contest_obj.num_winners,
        'reported_winners': contest_obj.reported_winners
    }
    contest_id = db.contests.find_one(query)['_id']
    query = {'reported': contest_id, 'underlying': 'tie', 'audit': audit_id, 'invalid_ballots': True, 'description' : 'Multi round Minerva (90% then 1.5x)'}
    sim = db.simulations.find_one(query)
    query = {'simulation' : sim['_id']}
    num_trials = db.trials.count_documents(query)
    print(contest, num_trials)
