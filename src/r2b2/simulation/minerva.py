import math
import random as r
from typing import List
from typing import Tuple

from r2b2.minerva import Minerva
from r2b2.simulator import Simulation
from r2b2.simulator import histogram


class MinervaOneRoundRisk(Simulation):
    """Simulate a 1-round Minerva audit for a given sample size to compute risk limit."""
    sample_size: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: Minerva

    def __init__(self,
                 alpha,
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
        super().__init__('minerva', alpha, reported, 'tie', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.sample_size = sample_size
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        self.reported.contest_ballots = self.total_relevant_ballots
        self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = Minerva(self.alpha, 1.0, self.reported)

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
        """Execute a 1-round minerva audit (using r2b2.minerva.Minerva)"""

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
        p_value = self.audit.compute_risk(sample[0], relevant_sample_size)
        if p_value <= self.alpha:
            stop = True
        else:
            stop = False

        return {
            'stop': stop,
            'p_value': p_value,
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

        if verbose:
            print('Analysis\n========')
            print('Underlying election is tied\n')
            print('Number of trials: {}'.format(num_trials))
            print('Number of stopped: {}'.format(stopped))
            print('Risk Limit: {:%}'.format(self.alpha))
            print('Risk Computed: {:%}'.format(stopped / num_trials))
        if hist:
            histogram(winner_ballot_dist, 'Winner ballots found in sample of size: {}'.format(self.sample_size))
            histogram(risk_dist, 'Risk (p_value) dist.')

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, (stopped / num_trials))
        return stopped / num_trials


class MinervaOneRoundStoppingProb(Simulation):
    """Simulate a 1-round Minerva audit for a given sample size to compute stopping probability."""
    sample_size: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: Minerva

    def __init__(self,
                 alpha,
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
        super().__init__('minerva', alpha, reported, 'reported', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.sample_size = sample_size
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        self.reported.contest_ballots = self.total_relevant_ballots
        self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = Minerva(self.alpha, 1.0, self.reported)

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
        """Execute a 1-round minerva audit."""

        r.seed(seed)

        # Draw a sample
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
        p_value = self.audit.compute_risk(sample[0], relevant_sample_size)
        if p_value <= self.alpha:
            stop = True
        else:
            stop = False

        return {
            'stop': stop,
            'p_value': p_value,
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

        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1

                winner_ballot_dist.append(trial['winner_ballots'])
                risk_dist.append(trial['p_value'])

        # TODO: insert verbose and histograms

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, (stopped / num_trials))
        return stopped / num_trials


class MinervaOneRoundAlteredMargin(Simulation):
    """Simulate a 1-round Minerva audit for a given sample size with a correct outcome but incorrect reported margin"""
    underlying_margin: float
    sample_size: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: Minerva

    def __init__(self,
                 alpha,
                 reported,
                 underlying,
                 underlying_margin,
                 sample_size,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 user='writer',
                 pwd='icanwrite',
                 *args,
                 **kwargs):
        super().__init__('minerva', alpha, reported, {
            'change': underlying,
            'margin': underlying_margin
        }, True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.underlying_margin = underlying_margin
        self.sample_size = sample_size
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        self.reported.contest_ballots = self.total_relevant_ballots
        self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = Minerva(self.alpha, 1.0, self.reported)

        if sample_size < self.audit.min_sample_size:
            raise ValueError('Sample size is less than minimum sample size for audit')

        # FIXME: sorted candidate list will be created by new branch, update once merged
        # Generate a sorted underlying vote distribution
        sorted_tally = sorted(self.reported.tally.items(), key=lambda x: x[1], reverse=True)
        underlying_winner_prop = (1.0 + underlying_margin) / 2.0
        self.vote_dist = [(sorted_tally[0][0], self.total_relevant_ballots * underlying_winner_prop)]
        # current = sorted_tally[0][1]
        # for i in range(1, len(sorted_tally)):
        #    current += sorted_tally[i][1]
        #    self.vote_dist.append((sorted_tally[i][0], current))
        for i in range(1, len(sorted_tally)):
            self.vote_dist.append((sorted_tally[i][0], self.total_relevant_ballots))
        self.vote_dist.append(('invalid', self.contest_ballots))

    def trial(self, seed):
        """Execute a 1-round minerva audit."""

        r.seed(seed)

        # Draw a sample
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
        p_value = self.audit.compute_risk(sample[0], relevant_sample_size)
        if p_value <= self.alpha:
            stop = True
        else:
            stop = False

        return {
            'stop': stop,
            'p_value': p_value,
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
        total_risk = 0.0

        for trial in trials:
            num_trials += 1
            total_risk += trial['p_value']
            if trial['stop']:
                stopped += 1
                winner_ballot_dist.append(trial['winner_ballots'])

        # TODO: insert verbose and histograms

        # Update simulation entry to include analysis
        if self.db_mode:
            analysis = {'avg_p_value': (total_risk / num_trials), 'sprob': (stopped / num_trials)}
            self.db.update_analysis(self.sim_id, analysis)

        return analysis


class MinervaRandomMultiRoundRisk(Simulation):
    """Simulate a multi-round Minerva audit for random subsequent sample sizes.

    The initial sample size, x, is given as input and further sample sizes are
    chosen randomly as an additioanl 0.5x to 1.5x ballots in the next round.
    The audit executes until it stops or reaches the maximum number of rounds.
    """
    sample_size: int
    max_rounds: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: Minerva

    def __init__(self,
                 alpha,
                 reported,
                 sample_size,
                 max_rounds,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 user='writer',
                 pwd='icanwrite',
                 *args,
                 **kwargs):
        if 'sim_args' in kwargs:
            kwargs['sim_args']['max_rounds'] = max_rounds
        else:
            kwargs['sim_args'] = {'max_rounds': max_rounds}
        super().__init__('minerva', alpha, reported, 'tie', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.sample_size = sample_size
        self.max_rounds = max_rounds
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        self.reported.contest_ballots = self.total_relevant_ballots
        self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = Minerva(self.alpha, 1.0, self.reported)

        if sample_size < self.audit.min_sample_size:
            raise ValueError('Sample size is less than minimum sample size for audit.')
        if max_rounds < 2:
            raise ValueError('Maximum rounds is too small.')

        # FIXME: sorted candidate list will be created by new branch, update once merged
        # Generate a sorted underlying vote distribution for a tied election
        sorted_tally = sorted(self.reported.tally.items(), key=lambda x: x[1], reverse=True)
        self.vote_dist = [(sorted_tally[0][0], self.total_relevant_ballots // 2)]
        for i in range(1, len(sorted_tally)):
            self.vote_dist.append((sorted_tally[i][0], self.total_relevant_ballots))
        self.vote_dist.append(('invalid', self.contest_ballots))

    def trial(self, seed):
        """Execute a 1-round minerva audit (using r2b2.minerva.Minerva)"""

        r.seed(seed)

        # Ensure audit is reset
        self.audit._reset()

        # Initialize first round with given initial sample size
        round_num = 1
        previous_sample_size = 0
        current_sample_size = self.sample_size
        stop = False

        # For each round
        sample = [0 for i in range(len(self.vote_dist))]
        while round_num <= self.max_rounds:
            # Draw a sample of a given size
            for i in range(current_sample_size - previous_sample_size):
                ballot = r.randint(1, self.contest_ballots)
                for j in range(len(sample)):
                    if ballot <= self.vote_dist[j][1]:
                        sample[j] += 1
                        break

            relevant_sample_size = current_sample_size - sample[-1]

            # Perform audit computations
            self.audit.rounds.append(relevant_sample_size)
            self.audit.current_dist_null()
            self.audit.current_dist_reported()
            # Check is audit has completed
            if (self.audit.stopping_condition(sample[0])):
                stop = True
            # Continue audit computations
            kmin = self.audit.next_min_winner_ballots(relevant_sample_size)
            self.audit.min_winner_ballots.append(kmin)
            self.audit.truncate_dist_null()
            self.audit.truncate_dist_reported()
            self.audit.sample_winner_ballots.append(sample[0])

            # If audit is done, return trial output
            # FIXME: Improve output format
            if stop:
                return {
                    'stop': stop,
                    'round': round_num,
                    'p_value_sched': self.audit.pvalue_schedule,
                    'p_value': self.audit.get_risk_level(),
                    'relevant_sample_size_sched': self.audit.rounds,
                    'winner_ballots_drawn_sched': self.audit.sample_winner_ballots,
                    'kmin_sched': self.audit.min_winner_ballots
                }

            # Else choose a next round size and continue
            round_num += 1
            sample_mult = r.uniform(0.5, 1.5)
            next_sample = math.ceil(self.sample_size * sample_mult)
            previous_sample_size = current_sample_size
            current_sample_size += next_sample

        # If audit does not stop, return trial output
        # FIXME: Improve output format
        return {
            'stop': stop,
            'round': self.max_rounds,
            'p_value_sched': self.audit.pvalue_schedule,
            'p_value': self.audit.get_risk_level(),
            'relevant_sample_size_sched': self.audit.rounds,
            'winner_ballots_drawn_sched': self.audit.sample_winner_ballots,
            'kmin_sched': self.audit.min_winner_ballots
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
        rounds_stopped = []
        # TODO: Create additinal structures to store trial data

        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1
                rounds_stopped.append(trial['round'])
            # TODO: Extract more data from trial

        if verbose:
            print('Analysis\n========\n')
            print('Number of trials: {}'.format(num_trials))
            print('Experiemtnal Risk: {:.5f}'.format(stopped / num_trials))
            if stopped > 0:
                print('Average Rounds in Stopped Trials: {:.2f}'.format(sum(rounds_stopped) / stopped))

        if hist:
            histogram(rounds_stopped, 'Rounds reached in stopped trials.')

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, (stopped / num_trials))
        return stopped / num_trials
