import json
import logging

from r2b2.simulation.minerva import MinervaOneRoundStoppingProb as MORSP 
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')
sample_size_file = 'data/2016_presidential_one_round_sample_sizes.json'


def state_trial(state, alpha, sample_size):
    sim = MORSP(alpha, election.contests[state], sample_size, sim_args={'description': 'Stopping Probability 90%: One round Minerva with given sample size (from PV MATLAB)'}, reported_args={'name': state, 'description': '2016 Presidential'})
    sim.run(10000)
    return sim.analyze()


if __name__=='__main__':
    with open(sample_size_file, 'r') as fd:
        sample_sizes = json.load(fd)
        for contest in election.contests.keys():
            if contest == 'Michigan':
                logging.warning('Michigan does not have sample sizes scaled from MATLAB, so its simulation is not run.')
                continue
            if contest == 'New Hampshire':
                logging.warning('New Hampshire margin too small, skipping.')
                continue
            sample_size = sample_sizes[contest]['Athena_pv_scaled']
            stopping_prob = state_trial(contest, 0.1, sample_size)
            logging.info('{}: {}'.format(contest, stopping_prob))
