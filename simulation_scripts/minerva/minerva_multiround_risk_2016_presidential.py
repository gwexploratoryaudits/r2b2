import json
import logging

from r2b2.simulation.minerva import MinervaRandomMultiRoundRisk as MRMRR
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')
sample_size_file = 'data/2016_presidential_one_round_sample_sizes.json'


def state_trial(state, alpha, sample_size):
    sim = MRMRR(
        alpha,
        election.contests[state],
        sample_size,
        5,
        sim_args={
            'description':
            'MutiRound Minerva with initial sample size from PV MATLAB, next rounds random multiple [0.5, 1.5] of initial sample size.'
        },
        reported_args={
            'name': state,
            'description': '2016 Presidential'
        })
    sim.run(10)
    return sim.analyze()


if __name__ == '__main__':
    with open(sample_size_file, 'r') as fd:
        sample_sizes = json.load(fd)
        for contest in election.contests.keys():
            winner_tally = election.contests[contest].tally[election.contests[contest].reported_winners[0]]
            tally = sum(election.contests[contest].tally.values())
            loser_tally = tally - winner_tally
            margin = (winner_tally - loser_tally) / tally
            if margin < 0.1:
                logging.warning('{} has a margin below 10%, so its simulation is not run.'.format(contest))
                continue

            sample_size = sample_sizes[contest]['Athena_pv_scaled']
            computed_risk = state_trial(contest, 0.1, sample_size)
            logging.info('{}: {}'.format(contest, computed_risk))
