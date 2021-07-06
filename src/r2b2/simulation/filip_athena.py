"""Athena/Minerva Simulations using Filip Zagorski's athena library."""

import random as r
from typing import List, Tuple

from athena.audit import Audit
from r2b2.simulator import Simulation, histogram


class FZMinervaOneRoundRisk(Simulation):
    """Simulate a 1-round Minerva audit for a given sample size to compute risk limit."""

    sample_size: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    election_file: str
    reported_name: str

    def __init__(self,
                 alpha,
                 reported,
                 sample_size,
                 election_file,
                 reported_name,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 *args,
                 **kwargs):
        super().__init__('fz_minerva', alpha, reported, 'tie', True, db_mode, db_host, db_port, db_name, args, kwargs)
        self.sample_size = sample_size
        self.total_relevant_ballots = sum(self.reported.tally.values())

        # Generate underlying vote distribution associated with a tie
        sorted_tally = sorted(self.reported.tally.items(), key=lambda x: x[1], reverse=True)
        self.vote_dist = [(sorted_tally[0][0], self.total_relevant_ballots // 2)]
        for i in range(1, len(sorted_tally)):
            self.vote_dist.append((sorted_tally[i][0], self.total_relevant_ballots))
        self.vote_dist.append(('invalid', self.reported.contest_ballots))

        # Store info needed to create an audit for each trial
        self.election_file = election_file
        self.reported_name = reported_name

    def trial(self, seed):
        """Execute a 1-round minerva audit from Filip's athena code."""

        # Create a clean audit object
        # FIXME: Ideally, there should be a way to create the audit object once
        # and reset it's state before each trial. Re-reading the election and
        # contest seems very inefficient...
        audit = Audit('minerva', self.alpha)
        audit.read_election_results(self.election_file)
        audit.load_contest(self.reported_name)

        r.seed(seed)

        # Draw a sample of given size
        sample = [0 for i in range(len(self.vote_dist))]
        for i in range(self.sample_size):
            ballot = r.randint(1, self.reported.contest_ballots)
            for j in range(len(sample)):
                if ballot <= self.vote_dist[j][1]:
                    sample[j] += 1
                    break

        relevant_sample_size = self.sample_size - sample[-1]

        # Perform audit calculations
        # FIXME: set_observations() will always print, let's not do that
        audit.set_observations(self.sample_size, relevant_sample_size, sample[:len(sample) - 1])
        p_value = audit.status[self.reported_name].risks[-1]

        if p_value > self.alpha and audit.status[self.reported_name].audit_completed:
            raise Exception('Risk limit not met, audit says completed')
        elif p_value <= self.alpha and not audit.status[self.reported_name].audit_completed:
            raise Exception('Risk limit met, audit says not complete.')

        return {
            'stop': audit.status[self.reported_name].audit_completed,
            'p_value': p_value,
            'sample_size': self.sample_size,
            'relevant_sample_size': relevant_sample_size,
            'winner_ballots': sample[0]
        }

    def analyze(self):
        if self.db_mode:
            trials = self.db.trial_lookup(self.sim_id)
        else:
            trials = self.trials
        num_trials = 0
        stopped = 0
        total_risk = 0
        total_relevant_sampled = 0
        winner_ballot_dist = []
        risk_dist = []

        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1

            total_relevant_sampled += trial['relevant_sample_size']
            winner_ballot_dist.append(trial['winner_ballots'])
            total_risk += trial['p_value']
            risk_dist.append(trial['p_value'])

        print('Analysis\n========')
        print('Underlying election is tied\n')
        print('Number of trials: {}'.format(num_trials))
        print('Number of stopped: {}'.format(stopped))
        print('Risk: {:%}'.format(stopped / num_trials))
        histogram(winner_ballot_dist, 'Winner ballots found in sample of size: {}'.format(self.sample_size))
        histogram(risk_dist, 'Risk (p_value) dist.')
