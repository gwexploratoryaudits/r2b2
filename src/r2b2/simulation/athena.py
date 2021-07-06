import random as r
from typing import List, Tuple

from r2b2.athena import Athena
from r2b2.simulator import Simulation, histogram


class AthenaOneRoundRisk(Simulation):
    """Simulate a 1-round Athena audit for a given sample size to compute risk limit."""
    delta: float
    sample_size: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: Athena

    def __init__(self,
                 alpha,
                 delta,
                 reported,
                 sample_size,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 user='writer',
                 pwd='icanwrite',
                 *args,
                 **kwargs):
        super().__init__('athena', alpha, reported, 'tie', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.sample_size = sample_size
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        self.reported.contest_ballots = self.total_relevant_ballots
        self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.delta = delta
        self.audit = Athena(self.alpha, self.delta, 1.0, self.reported)

        if sample_size < self.audit.min_sample_size:
            raise ValueError('Sample size is less than minimum sample size for audit.')

        # FIXME: sorted candidate list will be created by new branch, update once merged
        # Generate a sorted underlying vote distribution
        sorted_tally = sorted(self.reported.tally.items(), key=lambda x: x[1], reverse=True)
        self.vote_dist = [(sorted_tally[0][0], self.total_relevant_ballots // 2)]
        for i in range(1, len(sorted_tally)):
            self.vote_dist.append((sorted_tally[i][0], self.total_relevant_ballots))
        self.vote_dist.append(('invalid', self.contest_ballots))

    def trial(self, seed):
        """Execute a 1-round athena audit (using r2b2.athena.Athena)"""

        r.seed(seed)

        # Draw a sample of a given size
        sample = [0 for i in range(len(self.vote_dist))]
        for i in range(self.sample_size):
            ballot = r.randint(1, self.contest_ballots)
            for j in range(len(sample)):
                if ballot <= self.vote_dist[j][1]:
                    sample[j] += 1
                    break

        relevant_sample_size = self.sample_size - sample[-1]

        # Perform audit computations
        self.audit._reset()
        self.audit.rounds.append(relevant_sample_size)
        self.audit.current_dist_null()
        self.audit.current_dist_reported()
        point_null = self.audit.distribution_null[sample[0]]
        point_reported = self.audit.distribution_reported_tally[sample[0]]
        p_value = self.audit.compute_risk(sample[0], relevant_sample_size)
        if p_value <= self.alpha and self.delta * point_reported > point_null:
            stop = True
        else:
            stop = False

        return {
            'stop': stop,
            'p_value': p_value,
            'delta_computed': (point_null / point_reported),
            'sample_size': self.sample_size,
            'relevant_sample_size': relevant_sample_size,
            'winner_ballots': sample[0]
        }

    def analyze(self, verbose: bool = False, hist: bool = False):
        """Analyze trials to get experimental risk.

        Args:
            verbose (bool): If true, analyze will print simulation analysis information.
            hist (bool): If true, analyze will generate and display 2 histograms: winner
                ballots found in the sample size and computed risk.
        """
        if self.db_mode:
            trials = self.db.trial_lookup(self.sim_id)
        else:
            trials = self.trials
        num_trials = 0
        stopped = 0
        total_risk = 0
        total_delta = 0
        total_relevant_sampled = 0
        winner_ballot_dist = []
        risk_dist = []
        delta_dist = []

        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1

            total_relevant_sampled += trial['relevant_sample_size']
            winner_ballot_dist.append(trial['winner_ballots'])
            total_risk += trial['p_value']
            risk_dist.append(trial['p_value'])
            total_delta += trial['delta_computed']
            delta_dist.append(trial['delta_computed'])

        if verbose:
            print('Analysis\n========')
            print('Underlying election is tied\n')
            print('Number of trials: {}'.format(num_trials))
            print('Number of stopped: {}'.format(stopped))
            print('Risk Limit: {:%}'.format(self.alpha))
            print('Risk Computed: {:%}'.format(stopped / num_trials))
            print('Delta Condition: {}'.format(self.delta))
            print('Avg. Delta Computed: {}'.format(total_delta/num_trials))
        if hist:
            histogram(winner_ballot_dist, 'Winner ballots found in sample of size: {}'.format(self.sample_size))
            histogram(risk_dist, 'Risk (p_value) dist.')
            histogram(delta_dist, 'Delta (computed) dist.')

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, (stopped / num_trials))
        return stopped / num_trials


class AthenaOneRoundStoppingProb(Simulation):
    """Simulate a 1-round Athena audit for a given sample size to compute stopping probability."""
    delta: float
    sample_size: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: Athena

    def __init__(self,
                 alpha,
                 delta,
                 reported,
                 sample_size,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 user='writer',
                 pwd='icanwrite',
                 *args,
                 **kwargs):
        super().__init__('athena', alpha, reported, 'reported', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.delta = delta
        self.sample_size = sample_size
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        self.reported.contest_ballots = self.total_relevant_ballots
        self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = Athena(self.alpha, self.delta, 1.0, self.reported)

        if sample_size < self.audit.min_sample_size:
            raise ValueError('Sample size is less than minimum sample size for audit')

        # FIXME: sorted candidate list will be created by new branch, update once merged
        # Generate a sorted underlying vote distribution
        sorted_tally = sorted(self.reported.tally.items(), key=lambda x: x[1], reverse=True)
        self.vote_dist = [(sorted_tally[0][0], sorted_tally[0][1])]
        current = sorted_tally[0][1]
        for i in range(1, len(sorted_tally)):
            current += sorted_tally[i][1]
            self.vote_dist.append((sorted_tally[i][0], current))
        self.vote_dist.append(('invalid', self.contest_ballots))

    def trial(self, seed):
        """Execute a 1-round athena audit (using r2b2.athena.Athena)"""

        r.seed(seed)

        # Draw a sample of a given size
        sample = [0 for i in range(len(self.vote_dist))]
        for i in range(self.sample_size):
            ballot = r.randint(1, self.contest_ballots)
            for j in range(len(sample)):
                if ballot <= self.vote_dist[j][1]:
                    sample[j] += 1
                    break

        relevant_sample_size = self.sample_size - sample[-1]

        # Perform audit computations
        self.audit._reset()
        self.audit.rounds.append(relevant_sample_size)
        self.audit.current_dist_null()
        self.audit.current_dist_reported()
        point_null = self.audit.distribution_null[sample[0]]
        point_reported = self.audit.distribution_reported_tally[sample[0]]
        p_value = self.audit.compute_risk(sample[0], relevant_sample_size)
        if p_value <= self.alpha and self.delta * point_reported > point_null:
            stop = True
        else:
            stop = False

        return {
            'stop': stop,
            'p_value': p_value,
            'delta_computed': (point_null / point_reported),
            'sample_size': self.sample_size,
            'relevant_sample_size': relevant_sample_size,
            'winner_ballots': sample[0]
        }

    def analyze(self, verbose: bool = False, hist: bool = False):
        """Analyse trials to get experimental stopping probability"""
        if self.db_mode:
            trials = self.db.trial_lookup(self.sim_id)
        else:
            trials = self.trials
        num_trials = 0
        stopped = 0
        winner_ballot_dist = []
        risk_dist = []
        delta_dist = []

        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1

                winner_ballot_dist.append(trial['winner_ballots'])
                risk_dist.append(trial['p_value'])
                delta_dist.append(trial['delta_computed'])

        # TODO: insert verbose and histograms

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, (stopped / num_trials))
        return stopped / num_trials
