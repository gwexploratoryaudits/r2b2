from r2b2.minerva2 import Minerva2
from r2b2.contest import Contest
from r2b2.contest import ContestType
from scipy.stats import binom

# Get contest
contest_name = 'Virginia 2016 presidential contest'
tally = {'Hillary R. Clinton': 1981473, 'Donald J. Trump': 1769443, 'Gary Johnson': 118274, 'Evan McMullin':54054, 'Jill Stein':27638, 'All Others':33749}
reported_winner = max(tally, key=tally.get)
winner_votes = tally[reported_winner]
total_relevant = sum(tally.values())
loser_votes = total_relevant - winner_votes
margin = (winner_votes / total_relevant) - (loser_votes / total_relevant)
contest = Contest(total_relevant,
                            tally,
                            num_winners=1,
                            reported_winners=[reported_winner],
                            contest_type=ContestType.PLURALITY)
p = 1981473/ (1981473 + 1769443)

prop = (1981473+1769443)/(118274+54054+27638+33749+1981473+1769443)

# Create audit
M = Minerva2(.1, 1.0, contest)

# Execute a round of the audit for this sample
sample = {'Hillary R. Clinton': 100, 'Donald J. Trump': 100, 'Gary Johnson': 4, 'Evan McMullin':3, 'Jill Stein':1, 'All Others':1}
stop = M.execute_round(sum(sample.values()), sample)
res = M.next_sample_size(sprob=.1 ,linear_search=True)
print(stop)
print(res)
print(res*prop)

sample = {'Hillary R. Clinton': 200, 'Donald J. Trump': 200, 'Gary Johnson': 4, 'Evan McMullin':3, 'Jill Stein':1, 'All Others':1}
stop = M.execute_round(sum(sample.values()), sample)
res = M.next_sample_size(sprob=.1 ,linear_search=True)
print(stop)
print(res)
print(res*prop)

sample = {'Hillary R. Clinton': 300, 'Donald J. Trump': 300, 'Gary Johnson': 4, 'Evan McMullin':3, 'Jill Stein':1, 'All Others':1}
stop = M.execute_round(sum(sample.values()), sample)
res = M.next_sample_size(sprob=.1 ,linear_search=True)
print(stop)
print(res)
print(res*prop)

