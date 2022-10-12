import json
import logging
import math

from r2b2.minerva import Minerva
from r2b2.minerva2 import Minerva2
from r2b2.simulation.minerva import PerPrecinctMinervaMultiRoundStoppingProb as MMRSP
from r2b2.tests.util import parse_election
from r2b2.simulator import DBInterface
from r2b2.contest import Contest
from r2b2.contest import ContestType

from pymongo import MongoClient

# manually construct contest object from known values
contest_name = 'Alice and Bob Contest'
total_bals = 100000
margin = .01
tally = {'Alice':int(total_bals/2 + margin*total_bals),'Bob':int(total_bals - (total_bals/2 + margin*total_bals))}
reported_winner = max(tally, key=tally.get)
winner_votes = tally[reported_winner]
total_relevant = sum(tally.values())
loser_votes = total_relevant - winner_votes
margin = (winner_votes - loser_votes) / total_relevant
alpha = .1
print('margin '+str(margin))
# Make the contest object
contest = Contest(total_relevant,
                            tally,
                            num_winners=1,
                            reported_winners=[reported_winner],
                            contest_type=ContestType.PLURALITY)
print('Simulations for '+contest_name)

M1 = Minerva(alpha, 1.0, contest)
M2 = Minerva2(alpha, 1.0, contest)

pair = 'Alice-Bob'

sprob = .9
print('sprob '+str(sprob))
n1 = M1.next_sample_size(sprob=sprob)
print('n1 '+str(n1))

M1.compute_min_winner_ballots(M1.sub_audits[pair], [n1])
kmin1 = M1.sub_audits[pair].min_winner_ballots[-1]
print('kmin1 '+str(kmin1))
#print(M1.sub_audits[pair])

M2.compute_min_winner_ballots(M2.sub_audits[pair], n1)
kmin2 = M2.sub_audits[pair].min_winner_ballots[-1]
print('kmin2 '+str(kmin2))
#print(M2.sub_audits[pair])

print('now two cases:')
# close to kmin
samplegood = {'Alice':(kmin1-1),'Bob':(n1-(kmin1-1))}
print(samplegood)

# not close to kmin
samplebad = {'Alice':(math.ceil(n1/2)+1),'Bob':(n1-math.ceil(n1/2)-1)}
print(samplebad)

print('for good sample:')
M1 = Minerva(alpha, 1.0, contest)
M1.execute_round(n1,samplegood)
multiplier = 1.5
print('minerva for fixed round size '+str(math.ceil(n1+multiplier*n1))+' get sprob: '+str(M1.find_sprob(math.ceil(n1+multiplier*n1), M1.sub_audits[pair])[1]))

M2 = Minerva2(alpha, 1.0, contest)
M2.execute_round(n1,samplegood)
print('providence round size for '+str(sprob)+' sprob: '+str(M2.next_sample_size(sprob=sprob)))

print('for bad sample:')
M1 = Minerva(alpha, 1.0, contest)
M1.execute_round(n1,samplebad)
print('minerva for fixed round size '+str(math.ceil(n1+multiplier*n1))+' get sprob: '+str(M1.find_sprob(math.ceil(n1+multiplier*n1), M1.sub_audits[pair])[1]))

M2 = Minerva2(alpha, 1.0, contest)
M2.execute_round(n1,samplebad)
print('providence round size for '+str(sprob)+' sprob: '+str(M2.next_sample_size(sprob=sprob)))
















