import json
import logging

from r2b2.simulation.minerva import MinervaMultiRoundRisk as MMRR
from r2b2.tests.util import parse_election


election = parse_election('data/2020_presidential/2020_presidential.json')
sample_size_file = 'data/2020_presidential/2020_presidential_sample_sizes.json'


def state_trial(state, alpha, sample_size):
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
    sim.run(10000)
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
            if contest == 'Georgia' or contest == 'Wisconsin' or contest == 'Arizona':
                print('Skipping',contest)
                continue
            sample_size = sample_sizes[contest]['Minerva_pv_scaled'][0]
            computed_risk = state_trial(contest, 0.1, sample_size)
            logging.info('{}: {}'.format(contest, computed_risk))
