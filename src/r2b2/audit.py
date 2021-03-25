"""Abstract module defining an Audit framework."""
import math
from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List

import click
import numpy as np
from scipy.signal import convolve
from scipy.stats import binom
from scipy.stats import hypergeom

from r2b2.contest import Contest
from r2b2.contest import PairwiseContest


class PairwiseAudit():
    """Store audit information for pairwise comparison.

    The PairwiseAudit class hold the audit data for a single pair of candidates.

    Attributes:
        sub_contest (PairwiseContest): Pairwise contest data for relevant pair of candidates.
        min_sample_size (int): The smallest valid sample size. The minimum round size where
            kmin <= round
        risk_schedule (List[float]): Schedule of risk assocaited with each previous round.
            Corresponds to tail of null distribution.
        stopping_prob_schedule (List[float]): Schedule of stopping probabilities associated
            with each previous round. Corresponds to tail of reported tally distribution.
        pvalue_schedule (List[float]): Schedule of pvalues associated with each previous round.
            Corresponds to ratio of risk and stopping probability.
        distribution_null (Dict[str, List[float]]): Current distribution associated with a tied
            election for each pairwise subcontest.
        distribution_reported_tally (Dict[str, List[float]]): Current distribution associated
            with reported tally for each pairwise subcontest.
        min_winner_ballots (List[int]): List of stopping sizes (kmin values) for each round.
        stopped (bool): Indicates if pairwise audit has stopped.
    """

    sub_contest: PairwiseContest
    min_sample_size: int
    risk_schedule: List[float]
    stopping_prob_schedule: List[float]
    pvalue_schedule: List[float]
    distribution_null: List[float]
    distribution_reported_tally: List[float]
    min_winner_ballots: List[int]
    stopped: bool

    def __init__(self, sub_contest: PairwiseContest):
        self.sub_contest = sub_contest
        self.min_sample_size = 1
        self.risk_schedule = []
        self.stopping_prob_schedule = []
        self.pvalue_schedule = []
        self.distribution_null = [1.0]
        self.distribution_reported_tally = [1.0]
        self.min_winner_ballots = []
        self.stopped = False

    def __repr__(self):
        return 'winner: {}, loser: {}, min_sample_size: {}, risk_schedule: {}, sprob_schedule: {}, \
                pvalue_schedule: {}, min_winner_ballots: {}, stopped: {}'.format(self.sub_contest.reported_winner,
                                                                                 self.sub_contest.reported_loser, self.min_sample_size,
                                                                                 self.risk_schedule, self.stopping_prob_schedule,
                                                                                 self.pvalue_schedule, self.min_winner_ballots,
                                                                                 self.stopped)

    def __str__(self):
        title_str = 'Pairwise Audit\n--------------\n'
        sub_contest_str = 'Subcontest Winner: {}\n'.format(self.sub_contest.reported_winner)
        sub_contest_str += 'Subcontest Loser: {}\n'.format(self.sub_contest.reported_loser)
        min_sample_size_str = 'Minimum Sample Size: {}\n'.format(self.min_sample_size)
        risk_sched_str = 'Risk Schedule: {}\n'.format(self.risk_schedule)
        sprob_sched_str = 'Stopping Probability Schedule: {}\n'.format(self.stopping_prob_schedule)
        pval_str = 'p-Value Schedule: {}\n'.format(self.pvalue_schedule)
        min_win_ballot_str = 'Minimum Winner Ballots: {}\n'.format(self.min_winner_ballots)
        stop_str = 'Stopped: {}\n'.format(self.stopped)
        return (title_str + sub_contest_str + min_sample_size_str + risk_sched_str + sprob_sched_str + pval_str + min_win_ballot_str +
                stop_str + '\n')

    def _reset(self):
        self.risk_schedule = []
        self.stopping_prob_schedule = []
        self.pvalue_schedule = []
        self.distribution_null = [1.0]
        self.distribution_reported_tally = [1.0]
        self.min_winner_ballots = []
        self.stopped = False

    def get_pair_str(self):
        """Get winner-loser pair as string used as dictionary key in Audit."""
        return self.sub_contest.reported_winner + '-' + self.sub_contest.reported_loser


class Audit(ABC):
    """Abstract Base Class to define a general Audit object type.

    The Audit class is an abstract base class which defines the general structure and properties
    of a risk-limiting audit. Individual RLAs are subclasses of the Audit class.

    Attributes:
        alpha (float): Risk limit.  Alpha represents the chance that given an incorrectly called
            election, the audit will fail to go to a full recount.
        beta (float): the worst case chance of causing an unnecessary full recount. For many RLAs,
            beta will simply be set to 0 and will not appear to be a parameter.
        max_fraction_to_draw (float): The maximum total number of ballots auditors are willing to
            draw during the course of the audit.
        replacement (bool): Indicates if the audit sampling should be done with (true) or without
            (false) replacement.
        rounds (List[int]): List of round sizes (i.e. sample sizes).
        sample_ballots (Dict[str, List[int]]): Dictionary mapping candidates to sample counts drawn
            throughout audit. Sample counts are cumulative.
        pvalue_schedule (List[float]): Schedule of pvalues for overall audit in each round. In
            each round, the overall pvalue is the maximum pvalue of all subaudits.
        contest (Contest): Contest on which to run the audit.
        sub_audits (Dict[str, PairwiseAudit]): Dict of PairwiseAudits wthin audit indexed by loser.
        stopped (bool): Indicates if the audit has stopped (i.e. met the risk limit).
    """

    alpha: float
    beta: float
    max_fraction_to_draw: float
    replacement: bool
    rounds: List[int]
    sample_winner_ballots: List[int]
    pvalue_schedule: List[float]
    contest: Contest
    sample_ballots: Dict[str, List[int]]
    sub_audits: Dict[str, PairwiseAudit]
    stopped: bool

    def __init__(self, alpha: float, beta: float, max_fraction_to_draw: float, replacement: bool, contest: Contest):
        """Create an instance of an Audit.

        Note:
            This should only be called when initializing a subclass as the Audit class is an
            abstract class.
        """

        if type(alpha) is not float:
            raise TypeError('alpha must be a float.')
        if alpha < 0 or alpha > 1.0:
            raise ValueError('alpha value must be between 0 and 1.')
        if type(beta) is not float:
            raise TypeError('beta must be a float.')
        if beta < 0 or beta > 1.0:
            raise ValueError('beta must be between 0 and 1.')
        if type(max_fraction_to_draw) is not float:
            raise TypeError('max_fraction_to_draw must be a fraction (i.e. float).')
        if max_fraction_to_draw < 0 or max_fraction_to_draw > 1:
            raise ValueError('max_fraction_to_draw must be between 0 and 1')
        if type(replacement) is not bool:
            raise TypeError('replacement must be boolean.')
        if type(contest) is not Contest:
            raise TypeError('contest must be a Contest object')

        self.alpha = alpha
        self.beta = beta
        self.max_fraction_to_draw = max_fraction_to_draw
        self.replacement = replacement
        self.contest = contest
        self.rounds = []
        self.sample_winner_ballots = []
        self.pvalue_schedule = []
        self.stopped = False
        self.sample_ballots = {}
        for candidate in self.contest.candidates:
            self.sample_ballots[candidate] = []
        # Get pairwise subcontests for reported winners and create pairwise audits
        self.sub_audits = {}
        for sub_contest in self.contest.sub_contests:
            self.sub_audits[sub_contest.reported_winner + '-' + sub_contest.reported_loser] = PairwiseAudit(sub_contest)

    def __repr__(self):
        """String representation of Audit class.

        Note:
            Can (and perhaps should) be overwritten in subclass.
        """
        return '{}: [{}, {}, {}, {}, {}]'.format(self.__class__.__name__, self.alpha, self.beta, self.max_fraction_to_draw,
                                                 self.replacement, repr(self.contest))

    def __str__(self):
        """Human readable string (i.e. printable) representation of Audit class.

        Note:
            Can (and perhaps should) be overwritten in subclass.
        """
        title_str = 'Audit\n-----\n'
        alpha_str = 'Alpha: {}\n'.format(self.alpha)
        beta_str = 'Beta: {}\n'.format(self.beta)
        max_frac_str = 'Maximum Fraction to Draw: {}\n'.format(self.max_fraction_to_draw)
        replacement_str = 'Replacement: {}\n\n'.format(self.replacement)
        return title_str + alpha_str + beta_str + max_frac_str + replacement_str + str(self.contest)

    def current_dist_null(self):
        """Update distribution_null for each sub audit for current round."""
        if len(self.rounds) == 0:
            raise Exception('No rounds exist.')

        # For each pairwise sub audit, update null distribution
        for sub_audit in self.sub_audits.values():
            # Update pairwise distribution using pairwise sample total as round size
            self._current_dist_null_pairwise(sub_audit)

    def _current_dist_null_pairwise(self, sub_audit: PairwiseAudit, bulk_use_round_size=False):
        """Update distribution_null for a single PairwiseAudit

        Args:
            sub_audit (PairwiseAudit): Pairwise subaudit for which to update distribution.
            bulk_use_round_size (bool): Optional argument used by bulk methods. Since the bulk
                methods do not sample ballots for candidates during the rounds, this flag simply
                uses the round schedule as the round draw (instead of the pairwise round draw)
                for updating the distribution. Default is False.
        """
        pair = sub_audit.get_pair_str()
        # If not first round get marginal sample
        if bulk_use_round_size:
            if len(self.rounds) == 1:
                round_draw = self.rounds[0]
            else:
                round_draw = self.rounds[-1] - self.rounds[-2]
        elif len(self.rounds) == 1:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

            round_draw = self.sample_ballots[sub_audit.sub_contest.reported_loser][0] + self.sample_ballots[
                sub_audit.sub_contest.reported_winner][0]
        else:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))
            round_draw = (self.sample_ballots[sub_audit.sub_contest.reported_loser][-1] -
                          self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]) + (
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] -
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-2])
        # Distribution updating is dependent on sampling with or without replacement
        if self.replacement:
            distribution_round_draw = binom.pmf(range(0, round_draw + 1), round_draw, 0.5)
            # Compute convolution to get new distribution (except 1st round)
            if len(self.rounds) == 1:
                self.sub_audits[pair].distribution_null = distribution_round_draw
            else:
                self.sub_audits[pair].distribution_null = convolve(self.sub_audits[pair].distribution_null,
                                                                   distribution_round_draw,
                                                                   method='direct')
        else:
            half_contest_ballots = math.floor(sub_audit.sub_contest.contest_ballots / 2)
            if len(self.rounds) == 1:
                # Simply compute hypergeometric for 1st round distribution
                self.sub_audits[pair].distribution_null = hypergeom.pmf(np.arange(round_draw + 1), sub_audit.sub_contest.contest_ballots,
                                                                        half_contest_ballots, round_draw)
            else:
                distribution_round_draw = [0 for i in range(self.rounds[-1] + 1)]
                # Get relevant interval of previous round distribution
                interval = self.__get_interval(self.sub_audits[pair].distribution_null)
                # For every possible number of winner ballots in previous rounds
                # and every possibility in the current round
                # compute probability of their simultaneity
                for prev_round_possibility in range(interval[0], interval[1] + 1):
                    unsampled_contest_ballots = sub_audit.sub_contest.contest_ballots - self.rounds[-2]
                    unsampled_winner_ballots = half_contest_ballots - prev_round_possibility

                    curr_round_draw = hypergeom.pmf(np.arange(round_draw + 1), unsampled_contest_ballots, unsampled_winner_ballots,
                                                    round_draw)
                    for curr_round_possibility in range(round_draw + 1):
                        component_prob = sub_audit.distribution_null[prev_round_possibility] * curr_round_draw[curr_round_possibility]
                        distribution_round_draw[prev_round_possibility + curr_round_possibility] += component_prob
                self.sub_audits[pair].distribution_null = distribution_round_draw

    def current_dist_reported(self):
        """Update distribution_reported_tally for each subaudit for current round."""

        if len(self.rounds) == 0:
            raise Exception('No rounds exist')

        # For each pairwise sub audit, update dist_reported
        for sub_audit in self.sub_audits.values():
            # Update distr_reported using pairwise round size
            self._current_dist_reported_pairwise(sub_audit)

    def _current_dist_reported_pairwise(self, sub_audit: PairwiseAudit, bulk_use_round_size=False):
        """Update dist_reported for a single PairwiseAudit.

        Args:
            sub_audit (PairwiseAudit): Pairwise subaudit for which to update distriution.
            bulk_use_round_size (bool): Optional argument used by bulk methods. Since the bulk
                methods do not sample ballots for candidates during the rounds, this flag simply
                uses the round schedule as the round draw (instead of the pairwise round draw)
                for updating the distribution. Default is False.
        """

        pair = sub_audit.get_pair_str()
        # If not first round get marginal sample
        if bulk_use_round_size:
            if len(self.rounds) == 1:
                round_draw = self.rounds[0]
            else:
                round_draw = self.rounds[-1] - self.rounds[-2]
        elif len(self.rounds) == 1:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

            round_draw = self.sample_ballots[sub_audit.sub_contest.reported_loser][0] + self.sample_ballots[
                sub_audit.sub_contest.reported_winner][0]
        else:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

            round_draw = (self.sample_ballots[sub_audit.sub_contest.reported_loser][-1] -
                          self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]) + (
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] -
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-2])

        if self.replacement:
            distribution_round_draw = binom.pmf(range(0, round_draw + 1), round_draw, sub_audit.sub_contest.winner_prop)
            if len(self.rounds) == 1:
                self.sub_audits[pair].distribution_reported_tally = distribution_round_draw
            else:
                self.sub_audits[pair].distribution_reported_tally = convolve(sub_audit.distribution_reported_tally,
                                                                             distribution_round_draw,
                                                                             method='direct')
        else:
            reported_winner_ballots = int(sub_audit.sub_contest.winner_prop * sub_audit.sub_contest.contest_ballots)
            if len(self.rounds) == 1:
                # Simply compute hypergeometric for 1st round distribution
                self.sub_audits[pair].distribution_reported_tally = hypergeom.pmf(np.arange(round_draw + 1),
                                                                                  sub_audit.sub_contest.contest_ballots,
                                                                                  reported_winner_ballots, round_draw)
            else:
                distribution_round_draw = [0 for i in range(self.rounds[-1] + 1)]
                # Get relevant interval of previous round distribution
                interval = self.__get_interval(sub_audit.distribution_reported_tally)
                # For every possible number of winner ballots in previous rounds
                # and every possibility in the current round
                # compute probability of their simultaneity
                for prev_round_possibility in range(interval[0], interval[1] + 1):
                    unsampled_contest_ballots = self.sub_audits[pair].sub_contest.contest_ballots - self.rounds[-2]
                    unsampled_winner_ballots = reported_winner_ballots - prev_round_possibility

                    curr_round_draw = hypergeom.pmf(np.arange(round_draw + 1), unsampled_contest_ballots, unsampled_winner_ballots,
                                                    round_draw)
                    for curr_round_possibility in range(round_draw + 1):
                        component_prob = self.sub_audits[pair].distribution_reported_tally[prev_round_possibility] * curr_round_draw[
                            curr_round_possibility]
                        distribution_round_draw[prev_round_possibility + curr_round_possibility] += component_prob
                self.sub_audits[pair].distribution_reported_tally = distribution_round_draw

    def truncate_dist_null(self):
        """Update risk schedule and truncate null distribution for each subaudit."""
        for pair in self.sub_audits.keys():
            self._truncate_dist_null_pairwise(pair)

    def _truncate_dist_null_pairwise(self, pair: str):
        """Update risk schedule and truncate null distribution for a single subaudit.

        Args:
            pair (str): Dictionary key for subaudit (within the audit's subaudits) to truncate
                distribution and update risk schedule.
        """

        self.sub_audits[pair].risk_schedule.append(
            sum(self.sub_audits[pair].distribution_null[self.sub_audits[pair].min_winner_ballots[-1]:]))
        self.sub_audits[pair].distribution_null = self.sub_audits[pair].distribution_null[:self.sub_audits[pair].min_winner_ballots[-1]]

    def truncate_dist_reported(self):
        """Update stopping prob schedule and truncate reported distribution for each subaudit."""
        for pair in self.sub_audits.keys():
            self._truncate_dist_reported_pairwise(pair)

    def _truncate_dist_reported_pairwise(self, pair):
        """Update stopping prob schedule and truncate reported distribution for a single subaudit.

        Args:
            pair (str): Dictionary key for subaudit (within the audit's subaudits) to truncate
                distribution and update stopping prob schedule.
        """

        self.sub_audits[pair].stopping_prob_schedule.append(
            sum(self.sub_audits[pair].distribution_reported_tally[self.sub_audits[pair].min_winner_ballots[-1]:]))
        self.sub_audits[pair].distribution_reported_tally = self.sub_audits[pair].distribution_reported_tally[:self.sub_audits[pair].
                                                                                                              min_winner_ballots[-1]]

    def __get_interval(self, dist: List[float]):
        """Get relevant interval [l, u] of given distribution.

        Find levels l and u such that cdf(l) < tolerance and 1 - cdf(u) < tolerance. The purpose of
        this is to improve efficiency in the current_dist_* functions for audits without
        replacement where almost all of the hypergeometric distribution falls in a fraction of its
        range, i.e. between l and u.

        Note:
            cdf() in this context does not require cdf(infinity) = 1, although the distribution
            should sum very closely to 1.
        """

        tolerance = 0.0000001

        interval = [0, len(dist) - 1]
        lower_sum = 0
        upper_sum = 0

        # Handle the edge case of a small distribution
        if sum(dist) < 2 * tolerance:
            return interval

        for i in range(len(dist) - 1):
            lower_sum += dist[i]

            if (lower_sum + dist[i + 1]) > tolerance:
                interval[0] = i
                break

        for i in range(len(dist) - 1, 0, -1):
            upper_sum += dist[i]

            if (upper_sum + dist[i - 1]) > tolerance:
                interval[1] = i
                break
        return interval

    def asn(self, pair: str):
        """Compute ASN as described in BRAVO paper for pair of candidates.

        Given the fractional margin for the reported winner and the risk limit (alpha) produce the
        average number of ballots sampled during the audit.

        Args:
            pair (str): Dictionary key referencing pairwise audit in audit's subaudits.

        Returns:
            int: ASN value.
        """
        winner_prop = self.sub_audits[pair].sub_contest.winner_prop
        loser_prop = 1.0 - winner_prop
        margin = (2 * winner_prop) - 1
        z_w = math.log(margin + 1)
        z_l = math.log(1 - margin)
        top = (math.log(1.0 / self.alpha) + (z_w / 2.0))
        bottom = (winner_prop * z_w) + (loser_prop * z_l)
        return math.ceil(top / bottom)

    def execute_round(self, sample_size: int, sample: dict, verbose: bool = False) -> bool:
        """Execute a single, non-interactive audit round.

        Executes 1 round of the audit, given its current state. If the audit is stopped, its
        state will not be modified.

        Warning: This method assumes the audit is in the correct state to be executed. If multiple
            executions of a full audit will be run the same audit object, make sure to call reset
            on the audit object between full executions.

        Args:
            sample_size (int): Total ballots sampled by the end of this round (cumulative).
            sample (dict): Sample counts for each candidate by the end of this round (cumulative).

        Returns:
            bool: True if the audit met its stopping condition by this round.
        """

        if self.stopped:
            if verbose:
                click.echo('Audit already met the stopping condition in a previous round.')
            return True

        if len(self.rounds) > 0 and sample_size <= self.rounds[-1]:
            raise ValueError('Invlaid sample size, must be larger than previous round.')
        if len(self.rounds) > 0:
            for candidate, tally in sample.items():
                if tally < self.sample_ballots[candidate][-1]:
                    raise ValueError('Invalid sample count. Candidate {}\'s sample tally cannot decrease.'.format(candidate))
                if len(self.sample_ballots[candidate]) != len(self.rounds):
                    raise Exception('There are currently {} rounds, but only {} sample tallys for candidate {}.'.format(
                        len(self.rounds), len(self.sample_ballots[candidate]), candidate))
        if len(sample) != self.contest.num_candidates:
            raise Exception('Sample must include tally for all candidates.')

        self.rounds.append(sample_size)
        for candidate, tally in sample.items():
            self.sample_ballots[candidate].append(tally)
        self.current_dist_null()
        self.current_dist_reported()
        self.stopped = self.stopping_condition(verbose)
        if self.stopped:
            if verbose:
                click.echo('Audit had met stopping condition')
            return True

        self.next_min_winner_ballots(verbose)
        self.truncate_dist_null()
        self.truncate_dist_reported()
        return False

    def run(self, verbose: bool = False):
        """Begin interactive audit execution.

        Begins the interactive version of the audit. While computations for different audits will
        vary, the process for executing each one is the same. This provides a process for selecting
        a sample size, determining if the ballots found for the reported winner in that sample
        size meet the stopping condition(s), and if not continuing with the audit. As the audit
        proceeds, data including round sizes, ballots for the winner in each round size, and per
        round risk and stopping probability are stored.
        """

        self.__reset()
        click.echo('\n==================\nBeginning Audit...\n==================\n')
        # FIXME: no overall minimum sample size exists, so max of all sub audit mins used
        sample_size = max(sub_audit.min_sample_size for sub_audit in self.sub_audits.values())
        max_sample_size = self.contest.contest_ballots * self.max_fraction_to_draw
        prev_sample_size = 0
        curr_round = 0

        while sample_size < max_sample_size:
            curr_round += 1
            print('\n----------\n{:^10}\n----------\n'.format('Round {}'.format(curr_round)))

            if verbose and curr_round > 1:
                click.echo('\n+--------------------------------------------------+')
                click.echo('|{:^50}|'.format('Audit Statistics'))
                click.echo('|{:50}|'.format(' '))
                # FIXME: no more notion of overall audit minimum sample size
                # click.echo('|{:<50}|'.format('Minimum Sample Size: {}'.format(self.min_sample_size)))
                click.echo('|{:<30}{:<20}|'.format('Maximum Sample Size: ', max_sample_size))
                click.echo('|{:<30}{:<20}|'.format('Risk-Limit: ', self.alpha))
                click.echo('|{:<30}{:<20.12f}|'.format('Current Risk Level: ', self.get_risk_level()))
                click.echo('|{:50}|'.format(' '))
                click.echo('|{:^24}|{:^25}|'.format('Round', 'p-value'))
                click.echo('|------------------------|-------------------------|')
                for r in range(1, curr_round):
                    click.echo('|{:^24}|{:^25}|'.format(r, '{:.12f}'.format(self.pvalue_schedule[r - 1])))
                click.echo('+--------------------------------------------------+')

            # Get next round sample size given desired stopping probability
            while click.confirm('Would you like to enter a desired stopping probability for this round?'):
                desired_sprob = click.prompt('Enter desired stopping probability for this round (.9 recommended)',
                                             type=click.FloatRange(0, 1))
                next_sample_size = self.next_sample_size(desired_sprob)
                click.echo('{:<50}'.format('Recommended next sample size: {}'.format(next_sample_size)))

            if curr_round > 1:
                prev_sample_size = sample_size
            sample_size = click.prompt('Enter next sample size (as a running total)',
                                       type=click.IntRange(prev_sample_size + 1, max_sample_size))
            self.rounds.append(sample_size)

            # Get sample counts for each candidate drawn in this round
            sample_size_remaining = sample_size
            for candidate in self.contest.candidates:
                if curr_round == 1:
                    previous_votes_for_candidate = 0
                else:
                    previous_votes_for_candidate = self.sample_ballots[candidate][-1]
                if candidate in self.contest.reported_winners:
                    votes_for_candidate = click.prompt(
                        'Enter total number of votes for {} (reported winner) found in sample'.format(candidate),
                        type=click.IntRange(previous_votes_for_candidate, previous_votes_for_candidate + sample_size_remaining))
                else:
                    votes_for_candidate = click.prompt('Enter total number of votes for {} found in sample'.format(candidate),
                                                       type=click.IntRange(previous_votes_for_candidate,
                                                                           previous_votes_for_candidate + sample_size_remaining))
                self.sample_ballots[candidate].append(votes_for_candidate)
                sample_size_remaining -= votes_for_candidate

            # Update all pairwise distributions
            self.current_dist_null()
            self.current_dist_reported()

            # Evaluate Stopping Condition
            self.stopped = self.stopping_condition(verbose)
            click.echo('\n\n+----------------------------------------+')
            click.echo('|{:^40}|'.format('Stopping Condition Met? {}'.format(self.stopped)))
            click.echo('+----------------------------------------+')

            # Determine if the audit should proceed
            if self.stopped:
                click.echo('\n\nAudit Complete.')
                return
            elif click.confirm('\nWould you like to force stop the audit'):
                click.echo('\n\nAudit Complete: User stopped.')
                return

            # Compute kmin if audit has not stopped and truncate distributions
            self.next_min_winner_ballots(verbose)
            self.truncate_dist_null()
            self.truncate_dist_reported()

        click.echo('\n\nAudit Complete: Reached max sample size.')

    def __reset(self):
        """Reset attributes modified during run()."""

        self.rounds = []
        self.sample_winner_ballots = []
        self.pvalue_schedule = []
        for loser in self.sub_audits.keys():
            self.sub_audits[loser]._reset()
        self.stopped = False

    @abstractmethod
    def get_min_sample_size(self, sub_audit: PairwiseAudit):
        """Get the minimum valid sample size in a sub audit

        Args:
            sub_audit (PairwiseAudit): Get minimum sample size for this sub_audit.
        """

        pass

    @abstractmethod
    def next_sample_size(self, *args, **kwargs):
        """Generate estimates of possible next sample sizes.

        Note: To be used during live/interactive audit execution.
        """

        pass

    def stopping_condition(self, verbose: bool = False) -> bool:
        """Determine if the audits stopping condition has been met.

        The audit stopping condition is met if and only if each pairwise stopping condition
        is met.
        """
        stop = True
        max_pvalue = 0
        for pair in self.sub_audits.keys():
            # If pairwise audit has already stopped, do not compute round
            if self.sub_audits[pair].stopped:
                continue
            # Evaluate stopping condition for pairwise audit
            if not self.stopping_condition_pairwise(pair, verbose):
                stop = False
            if self.sub_audits[pair].pvalue_schedule[-1] > max_pvalue:
                max_pvalue = self.sub_audits[pair].pvalue_schedule[-1]
        self.pvalue_schedule.append(max_pvalue)
        if verbose:
            click.echo('\nRisk Level: {}'.format(self.get_risk_level()))
        return stop

    @abstractmethod
    def stopping_condition_pairwise(self, pair: str, verbose: bool = False) -> bool:
        """Determine if pairwise subcontest meets stopping condition.

        Args:
            pair (str): Dictionary key referencing pairwise audit in audit's sub_audits.

        Returns:
            bool: If the pairwise subaudit has stopped.
        """

        pass

    def next_min_winner_ballots(self, verbose: bool = False):
        """Compute next stopping size of given (actual) sample sizes for all subaudits."""
        if verbose:
            click.echo('\n+----------------------------------------+')
            click.echo('|{:^40}|'.format('Minimum Winner Ballots Needed in Round'))
            click.echo('|{:^40}|'.format('--------------------------------------'))
        for pair, sub_audit in self.sub_audits.items():
            kmin = self.next_min_winner_ballots_pairwise(sub_audit)
            self.sub_audits[pair].min_winner_ballots.append(kmin)
            if verbose:
                if kmin is None:
                    kmin = 'Inf.'
                click.echo('|{:<30} {:<9}|'.format(pair, kmin))
        if verbose:
            click.echo('\n+----------------------------------------+')

    @abstractmethod
    def next_min_winner_ballots_pairwise(self, sub_audit: PairwiseAudit) -> int:
        """Compute next stopping size of given (actual) sample size for a subaudit.

        Args:
            sub_audit (PairwiseAudit): Compute next stopping size for this subaudit.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def compute_min_winner_ballots(self, sub_audit: PairwiseAudit, progress: bool = False, *args, **kwargs):
        """Compute the stopping size(s) for any number of sample sizes for a given subaudit."""

        pass

    @abstractmethod
    def compute_all_min_winner_ballots(self, sub_audit: PairwiseAudit, progress: bool = False, *args, **kwargs):
        """Compute all stopping sizes from the minimum sample size on for a given subaudit."""

        pass

    @abstractmethod
    def compute_risk(self, sub_audit: PairwiseAudit, *args, **kwargs):
        """Compute the current risk level of a given subaudit.

        Returns:
            Current risk level of the audit (as defined per audit implementation).
        """

        pass

    @abstractmethod
    def get_risk_level(self, *args, **kwargs):
        """Find the risk level of the audit, that is, the smallest risk limit for which the audit
        as it has panned out would have already stopped.

        Returns:
            float: Risk level of the realization of the audit.
        """

        pass
