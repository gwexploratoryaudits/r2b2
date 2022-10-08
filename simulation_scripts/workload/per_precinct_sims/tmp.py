"""
Script to run the simulations presented in the workload/multiple rounds section of the Providence paper.

Simulations assume that the announced results are correct (ie draws from the distribution specified by the reported margin. 
Contest: 2020 US Presidential contest, Pennsylvania state-wide
Alpha: 10\%
"""

import json
import logging

from r2b2.tests.util import parse_election
from r2b2.simulator import DBInterface
from r2b2.contest import Contest
from r2b2.contest import ContestType

from pymongo import MongoClient
# manually construct contest object from known values
contest_name = 'Virginia 2016 presidential contest'
tally = {'Hillary R. Clinton': 1981473, 'Donald J. Trump': 1769443, 'Gary Johnson': 118274, 'Evan McMullin':54054, 'Jill Stein':27638, 'All Others':33749}
reported_winner = max(tally, key=tally.get)
winner_votes = tally[reported_winner]
total_relevant = sum(tally.values())
loser_votes = 1769443
margin = (winner_votes / total_relevant) - (loser_votes / total_relevant)
#margin = (1981473-1769443) / (1981473+1769443)

print(margin)
