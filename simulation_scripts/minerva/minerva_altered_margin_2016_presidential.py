import json
import logging

from r2b2.simulation.minerva import MinervaOneRoundAlteredMargin as MORAM
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')
sample_size_file = 'data/2016_presidential_one_round_sample_sizes.json'


def state_trial_plus10(state, alpha, sample_size, underlying_margin):
    sim = MORAM(alpha,
                election.contests[state],
                'plus10%',
                underlying_margin,
                sample_size,
                sim_args={'description': 'Altered Margin+10%: One round Minerva with given sample size (from PV MATLAB)'},
                reported_args={
                    'name': state,
                    'description': '2016 Presidential'
                })
    sim.run(10000)
    return sim.analyze()


def state_trial_minus10(state, alpha, sample_size, underlying_margin):
    sim = MORAM(alpha,
                election.contests[state],
                'minus10%',
                underlying_margin,
                sample_size,
                sim_args={'description': 'Altered Margin-10%: One round Minerva with given sample size (from PV MATLAB)'},
                reported_args={
                    'name': state,
                    'description': '2016 Presidential'
                })
    sim.run(10000)
    return sim.analyze()


if __name__ == '__main__':
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

            # Compute current margin
            # FIXME: this includes the correction for relevant ballots that is currently
            # in another branch
            contest_obj = election.contests[contest]
            relevant_ballots = sum(contest_obj.tally.values())
            winner_prop = contest_obj.tally[contest_obj.reported_winners[0]] / relevant_ballots
            margin = (2.0 * winner_prop) - 1.0

            # Compute altered margins
            margin_plus10 = 1.10 * margin
            margin_minus10 = 0.9 * margin

            # Run trials for each altered margin
            state_trial_plus10(contest, 0.1, sample_size, margin_plus10)
            state_trial_minus10(contest, 0.1, sample_size, margin_minus10)

            print('{} DONE'.format(contest))
