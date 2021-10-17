import math
import random as r
from typing import List
from typing import Tuple

from r2b2.so_bravo import SO_BRAVO
from r2b2.simulator import Simulation
from r2b2.simulator import histogram

import time

class SO_BRAVOMultiRoundStoppingProb(Simulation):
    """Simulate a multiround SO_BRAVO audit.

    If sample_sprob is provided, sample sizes to achieve a sample_sprob
    probability of stopping will be computed and used. Otherwise,
    the initial sample size, sample_size, is given as input and further sample
    sizes are an additional (sample_mult) * (sample_size)  ballots.
    The audit executes until it stops or reaches the maximum number of rounds.
    """
    sample_sprob: float
    sample_size: int
    sample_mult: float
    max_rounds: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: SO_BRAVO

    def __init__(self,
                 alpha,
                 reported,
                 max_rounds,
                 sample_size=None,
                 sample_mult=None,
                 sample_sprob=None,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 user='writer',
                 pwd='icanwrite',
                 *args,
                 **kwargs):
        # Add parameters to simulation DB entry
        if 'sim_args' in kwargs:
            kwargs['sim_args']['max_rounds'] = max_rounds
            kwargs['sim_args']['sample_mult'] = sample_mult
            kwargs['sim_args']['sample_sprob'] = sample_sprob
        else:
            kwargs['sim_args'] = {'max_rounds': max_rounds, 'sample_mult': sample_mult, 'sample_sprob': sample_sprob}
        super().__init__('so_bravo', alpha, reported, 'reported', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.sample_sprob = sample_sprob
        self.sample_size = sample_size
        self.sample_mult = sample_mult
        self.max_rounds = max_rounds
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        # self.reported.contest_ballots = self.total_relevant_ballots
        # self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = SO_BRAVO(self.alpha, 1.0, self.reported)

        if sample_sprob is None and sample_size is None and sample_mult is None:
            raise ValueError('Sample sizes cannot be chosen without sample_sprob or sample_size and sample_mult.')
        if sample_sprob is not None:
            if not sample_sprob > 0 or not sample_sprob < 1:
                raise ValueError('Sample size stopping probability is not between 0 and 1.')
        else:
            min_sample_size = 0
            for pairwise_audit in self.audit.sub_audits.values():
                min_sample_size = max(pairwise_audit.min_sample_size, min_sample_size)
            if sample_size < min_sample_size:
                raise ValueError('Sample size is less than minimum sample size for audit.')
        if max_rounds < 2:
            raise ValueError('Maximum rounds is too small.')

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
        """Execute a multiround so_bravo audit (using r2b2.so_bravo.SO_BRAVO)"""

        r.seed(seed)

        # Ensure audit is reset
        self.audit._reset()

        # Initialize first round including initial sample size
        round_num = 1
        previous_sample_size = 0
        if self.sample_sprob is not None:
            start = time.time()
            current_sample_size = self.audit.next_sample_size(self.sample_sprob)
            elapsed = time.time() - start
            print(elapsed, "elapsed during next_sample_size")
        else:
            current_sample_size = self.sample_size
            next_sample = math.ceil(self.sample_mult * self.sample_size)
        stop = False

        # For each round
        sample = [0 for i in range(len(self.vote_dist))]
        while round_num <= self.max_rounds:
            # Reset empty lists for the selection-order tracking this round
            so_samples = [[] for i in range(len(self.vote_dist))]
            # Draw a sample of a given size for this round
            for i in range(current_sample_size - previous_sample_size):
                ballot = r.randint(1, self.contest_ballots)
                # Find candidate j for whom this ballot was cast.
                for j in range(len(sample)):
                    if ballot <= self.vote_dist[j][1]:
                        # Increment the tally for candidate j.
                        sample[j] += 1
                        # Update the Selection-Ordered samples for all candidates.
                        for k in range(len(sample)):
                            if k == j:
                                # This ballot is for candidate k.
                                so_samples[k].append(1)
                            else:
                                # This ballot is not for candidate k.
                                so_samples[k].append(0)
                        break

            # Convert this sample to a dict
            sample_dict = {}
            for i in range(len(self.vote_dist)):
                # For now, we will ignore the irrelevant ballots
                if not self.vote_dist[i][0] == 'invalid':
                    sample_dict[self.vote_dist[i][0]] = sample[i]
                    sample_dict[self.vote_dist[i][0]+'_so'] = so_samples[i]

            # Execute a round of the audit for this sample
            start = time.time()
            stop = self.audit.execute_round(current_sample_size, sample_dict)
            elapsed = time.time() - start
            print(elapsed, "elapsed during execute_round")

            # If audit is done, return trial output
            # FIXME: Improve output format
            if stop:
                return {
                    'stop': stop,
                    'round': round_num,
                    'p_value_sched': self.audit.pvalue_schedule,
                    'p_value': self.audit.get_risk_level(),
                    'relevant_sample_size_sched': self.audit.rounds,
                    'winner_ballots_drawn_sched': self.audit.sample_ballots
                    # 'kmin_sched': self.audit.min_winner_ballots
                }

            # Else choose a next round size and continue
            round_num += 1
            previous_sample_size = current_sample_size
            if self.sample_sprob is not None:
                current_sample_size = self.audit.next_sample_size(self.sample_sprob)
            else:
                current_sample_size += next_sample
                next_sample = math.ceil(self.sample_mult * self.sample_size)

        # If audit does not stop, return trial output
        # FIXME: Improve output format
        return {
            'stop': stop,
            'round': self.max_rounds,
            'p_value_sched': self.audit.pvalue_schedule,
            'p_value': self.audit.get_risk_level(),
            'relevant_sample_size_sched': self.audit.rounds,
            'winner_ballots_drawn_sched': self.audit.sample_ballots
            # 'kmin_sched': self.audit.min_winner_ballots
        }

    def analyze(self, verbose: bool = False, hist: bool = False):
        """Analyze trials to get experimental stopping probability.

        Args:
            verbose (bool): If true, analyze will print simulation analysis information.
            hist (bool): If true, analyze will generate and display 2 histograms: winner
                ballots found in the sample size and computed stopping probability.
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
            print('Experiemtnal Stopping Prob: {:.5f}'.format(stopped / num_trials))
            if stopped > 0:
                print('Average Rounds in Stopped Trials: {:.2f}'.format(sum(rounds_stopped) / stopped))

        if hist:
            histogram(rounds_stopped, 'Rounds reached in stopped trials.')

        # Find stopping probability for each round
        sprob_by_round = [0]*self.max_rounds
        stopped_by_round = [0]*self.max_rounds
        remaining_by_round = [0]*(self.max_rounds+1)
        # first round has all remaining
        remaining_by_round[0] = num_trials

        for rd in range(1, self.max_rounds+1):
            stopped_this_round = rounds_stopped.count(rd)
            stopped_by_round[rd-1] = stopped_this_round
            if remaining_by_round[rd-1] != 0:
                sprob_by_round[rd-1] = stopped_this_round/remaining_by_round[rd-1]
            else:
                sprob_by_round[rd-1] = -1
            remaining_by_round[rd] = remaining_by_round[rd-1]-stopped_this_round

        analysis = {
            'sprob': stopped / num_trials,
            'sprob_by_round': sprob_by_round,
            'remaining_by_round': remaining_by_round,
            'stopped_by_round': stopped_by_round
        }

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, analysis)

        return analysis


class SO_BRAVOMultiRoundRisk(Simulation):
    """Simulate a multiround SO_BRAVO audit.

    If sample_sprob is provided, sample sizes to achieve a sample_sprob
    probability of stopping will be computed and used. Otherwise,
    the initial sample size, x, is given as input and further sample sizes are
    an additional (sample_mult) * x ballots.
    The audit executes until it stops or reaches the maximum number of rounds.
    """
    sample_sprob: float
    sample_size: int
    sample_mult: float
    max_rounds: int
    total_relevant_ballots: int
    vote_dist: List[Tuple[str, int]]
    audit: SO_BRAVO

    def __init__(self,
                 alpha,
                 reported,
                 max_rounds,
                 sample_size=None,
                 sample_mult=None,
                 sample_sprob=None,
                 db_mode=True,
                 db_host='localhost',
                 db_name='r2b2',
                 db_port=27017,
                 user='writer',
                 pwd='icanwrite',
                 *args,
                 **kwargs):
        # Add parameters to simulation DB entry
        if 'sim_args' in kwargs:
            kwargs['sim_args']['max_rounds'] = max_rounds
            kwargs['sim_args']['sample_mult'] = sample_mult
            kwargs['sim_args']['sample_sprob'] = sample_sprob
        else:
            kwargs['sim_args'] = {'max_rounds': max_rounds, 'sample_mult': sample_mult, 'sample_sprob': sample_sprob}
        super().__init__('so_bravo', alpha, reported, 'tie', True, db_mode, db_host, db_port, db_name, user, pwd, *args, **kwargs)
        self.sample_size = sample_size
        self.sample_mult = sample_mult
        self.sample_sprob = sample_sprob
        self.max_rounds = max_rounds
        self.total_relevant_ballots = sum(self.reported.tally.values())
        # FIXME: temporary until pairwise contest fix is implemented
        self.contest_ballots = self.reported.contest_ballots
        # self.reported.contest_ballots = self.total_relevant_ballots
        # self.reported.winner_prop = self.reported.tally[self.reported.reported_winners[0]] / self.reported.contest_ballots
        self.audit = SO_BRAVO(self.alpha, 1.0, self.reported)

        if sample_sprob is None and sample_size is None and sample_mult is None:
            raise ValueError('Sample sizes cannot be chosen without sample_sprob or sample_size and sample_mult.')
        if sample_sprob is not None:
            if not sample_sprob > 0 or not sample_sprob < 1:
                raise ValueError('Sample size stopping probability is not between 0 and 1.')
        else:
            min_sample_size = 0
            for pairwise_audit in self.audit.sub_audits.values():
                min_sample_size = max(pairwise_audit.min_sample_size, min_sample_size)
            if sample_size < min_sample_size:
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
        """Execute a multiround so_bravo audit (using r2b2.so_bravo.SO_BRAVO)"""

        r.seed(seed)

        # Ensure audit is reset
        self.audit._reset()

        # Initialize first round including initial sample size
        round_num = 1
        previous_sample_size = 0
        if self.sample_sprob is None:
            current_sample_size = self.sample_size
            next_sample = math.ceil(self.sample_mult * self.sample_size)
        stop = False

        # For each round
        sample = [0 for i in range(len(self.vote_dist))]
        while round_num <= self.max_rounds:
            # Reset empty lists for the selection-order tracking this round
            so_samples = [[] for i in range(len(self.vote_dist))]
            if self.sample_sprob is not None:
                start = time.time()
                current_sample_size = self.audit.next_sample_size(self.sample_sprob)
                print(time.time() - start, "elapsed in next_sample_size")
            # Draw a sample of a given size
            for i in range(current_sample_size - previous_sample_size):
                ballot = r.randint(1, self.contest_ballots)
                for j in range(len(sample)):
                    if ballot <= self.vote_dist[j][1]:
                        sample[j] += 1
                        # Update the Selection-Ordered samples for all candidates.
                        for k in range(len(sample)):
                            if k == j:
                                # This ballot is for candidate k=j.
                                so_samples[k].append(1)
                            else:
                                # This ballot is not for candidate k.
                                so_samples[k].append(0)
                        break

            # Convert this sample to a dict
            sample_dict = {}
            for i in range(len(self.vote_dist)):
                # For now, we will ignore the irrelevant ballots
                if not self.vote_dist[i][0] == 'invalid':
                    sample_dict[self.vote_dist[i][0]] = sample[i]
                    sample_dict[self.vote_dist[i][0]+'_so'] = so_samples[i]

            # Execute a round of the audit for this sample
            start = time.time()
            stop = self.audit.execute_round(current_sample_size, sample_dict)
            print(time.time() - start, "elapsed in execute_round")

            # If audit is done, return trial output
            # FIXME: Improve output format
            if stop:
                return {
                    'stop': stop,
                    'round': round_num,
                    'p_value_sched': self.audit.pvalue_schedule,
                    'p_value': self.audit.get_risk_level(),
                    'relevant_sample_size_sched': self.audit.rounds,
                    'winner_ballots_drawn_sched': self.audit.sample_ballots,
                    # 'kmin_sched': self.audit.min_winner_ballots
                }

            # Else choose a next round size and continue
            round_num += 1
            previous_sample_size = current_sample_size
            if self.sample_sprob is None:
                current_sample_size += next_sample
                next_sample = math.ceil(self.sample_mult * self.sample_size)

        # If audit does not stop, return trial output
        # FIXME: Improve output format
        return {
            'stop': stop,
            'round': self.max_rounds,
            'p_value_sched': self.audit.pvalue_schedule,
            'p_value': self.audit.get_risk_level(),
            'relevant_sample_size_sched': self.audit.rounds,
            'winner_ballots_drawn_sched': self.audit.sample_ballots,
            # 'kmin_sched': self.audit.min_winner_ballots
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

        # Find risk for each round
        risk_by_round = [0]*self.max_rounds
        stopped_by_round = [0]*self.max_rounds
        remaining_by_round = [0]*(self.max_rounds+1)
        # first round has all remaining
        remaining_by_round[0] = num_trials

        for rd in range(1, self.max_rounds + 1):
            stopped_this_round = rounds_stopped.count(rd)
            stopped_by_round[rd-1] = stopped_this_round
            if remaining_by_round[rd-1] != 0:
                risk_by_round[rd-1] = stopped_this_round/remaining_by_round[rd-1]
            else:
                risk_by_round[rd-1] = -1
            remaining_by_round[rd] = remaining_by_round[rd-1]-stopped_this_round

        analysis = {
            'risk': stopped / num_trials,
            'risk_by_round': risk_by_round,
            'remaining_by_round': remaining_by_round,
            'stopped_by_round': stopped_by_round
        }

        # Update simulation entry to include analysis
        if self.db_mode:
            self.db.update_analysis(self.sim_id, analysis)

        return analysis
