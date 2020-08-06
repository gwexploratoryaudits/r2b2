import json
import logging

from r2b2.simulation.filip_athena import FZMinervaOneRoundRisk as FZMOR
from r2b2.tests.util import parse_election

election_name = 'data/2016_presidential.json'
election = parse_election(election_name)
sample_size_file = 'data/2016_presidential_one_round_sample_sizes.json'


def state_trial(state, alpha, sample_size):
    sim = FZMOR(alpha,
                election.contests[state],
                sample_size,
                election_name,
                state,
                sim_args={'description': 'One round Minerva (from fz athena repo) with given sample size (from PV MATLAB)'},
                reported_args={
                    'name': state,
                    'description': '2016 Presidential'
                })
    sim.run(10000)


if __name__ == '__main__':
    with open(sample_size_file, 'r') as fd:
        sample_sizes = json.load(fd)
        for contest in election.contests.keys():
            if contest == 'Michigan':
                logging.warning('Michigan does not have sample sizes from MATLAB, so its simulation is not run.')
                continue
            sample_size = sample_sizes[contest]['Athena_pv_scaled']
            state_trial(contest, 0.1, sample_size)
