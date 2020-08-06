import json
import logging

from r2b2.simulation.minerva import MinervaOneRoundRisk as MORR
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')
sample_size_file = 'data/2016_presidential_one_round_sample_sizes.json'


def state_trial(state, alpha, sample_size):
    sim = MORR(alpha, election.contests[state], sample_size, reported_name=state, sim_args={'description': 'One round Minerva with given sample size (from PV MATLAB)'}, reported_args={'name': state, 'description': '2016 Presidential'})
    sim.run(10000)


if __name__=='__main__':
    with open(sample_size_file, 'r') as fd:
        sample_sizes = json.load(fd)
        for contest in election.contests.keys():
            if contest == 'Michigan':
                logging.warning('Michigan does not have sample sizes scaled from MATLAB, so its simulation is not run.')
                continue
            sample_size = sample_sizes[contest]['Athena_pv_scaled']
