"""Abstract module defining an Audit framework."""
import math
from abc import ABC
from abc import abstractmethod
from typing import List

import numpy as np
from scipy.signal import fftconvolve
from scipy.stats import binom
from scipy.stats import hypergeom

from r2b2.contest import Contest


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
        min_sample_size (int): The smallest valid sample size. The minimum round size where
            kmin <= round size
        rounds (List[int]): List of round sizes (i.e. sample sizes).
        min_winner_ballots (List[int]): List of stopping sizes (kmin values) for each round size in
            rounds.
        sample_winner_ballots (List[int]): List of ballots found for the reported winner in each
            round size.
        risk_schedule (List[float]): Schedule of risk associated with each previous round.
            Corresponds to tail of null distribution.
        stopping_prob_schedule (List[float]): Schedule of stopping probabilities associated
            with each previous round. Corresponds to tail of reported tally distribution.
        distribution_null (List[float]): Current distribution associated with a tied election.
        distribution_reported_tally (List[float]): Current distribution associated with reported
            tally.
        contest (Contest): Contest on which to run the audit.
    """

    alpha: float
    beta: float
    max_fraction_to_draw: float
    replacement: bool
    min_sample_size: int
    rounds: List[int]
    min_winner_ballots: List[int]
    sample_winner_ballots: List[int]
    risk_schedule: List[float]
    stopping_prob_schedule: List[float]
    distribution_null: List[float]
    distribution_reported_tally: List[float]
    contest: Contest

    def __init__(self, alpha: float, beta: float, max_fraction_to_draw: float,
                 replacement: bool, contest: Contest):
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
            raise TypeError(
                'max_fraction_to_draw must be a fraction (i.e. float).')
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
        self.min_sample_size = 1
        self.rounds = []
        self.min_winner_ballots = []
        self.sample_winner_ballots = []
        self.risk_schedule = []
        self.stopping_prob_schedule = []
        self.distribution_null = [1.0]
        self.distribution_reported_tally = [1.0]

    def current_dist_null(self, kmin: int):
        """Update distribution null and risk schedule for current round."""

        if len(self.rounds) == 1:
            round_draw = self.rounds[0]
        else:
            round_draw = self.rounds[-1] - self.rounds[-2]

        # Distribution updating is dependent on sampling with or without replacement
        if self.replacement:
            distribution_round_draw = binom.pmf(range(0, round_draw + 1),
                                                round_draw, 0.5)
            # Compute convolution to get new distribution (except 1st round)
            if len(self.rounds) == 1:
                self.distribution_null = distribution_round_draw
            else:
                self.distribution_null = fftconvolve(self.distribution_null,
                                                     distribution_round_draw)
        else:
            half_contest_ballots = math.floor(self.contest.contest_ballots / 2)
            if len(self.rounds) == 1:
                # Simply compute hypergeometric for 1st round distribution
                self.distribution_null = hypergeom.pmf(
                    np.arange(round_draw + 1), self.contest.contest_ballots,
                    half_contest_ballots, round_draw)
            else:
                distribution_round_draw = [
                    0 for i in range(self.rounds[-1] + 1)
                ]
                # Get relevant interval of previous round distribution
                interval = self.__get_interval(self.distribution_null)
                # For every possible number of winner ballots in previous rounds
                # and every possibility in the current round
                # compute probability of their simultaneity
                for prev_round_possibility in range(interval[0],
                                                    interval[1] + 1):
                    unsampled_contest_ballots = self.contest.contest_ballots - self.rounds[
                        -2]
                    unsampled_winner_ballots = half_contest_ballots - prev_round_possibility

                    curr_round_draw = hypergeom.pmf(np.arange(round_draw + 1),
                                                    unsampled_contest_ballots,
                                                    unsampled_winner_ballots,
                                                    round_draw)
                    for curr_round_possibility in range(round_draw + 1):
                        component_prob = self.distribution_null[
                            prev_round_possibility] * curr_round_draw[
                                curr_round_possibility]
                        distribution_round_draw[
                            prev_round_possibility +
                            curr_round_possibility] += component_prob
                self.distribution_null = distribution_round_draw

        self.risk_schedule.append(sum(self.distribution_null[kmin + 1:]))
        self.distribution_null = self.distribution_null[:kmin + 1]

    def current_dist_reported(self, kmin: int):
        """Update distribution_reported_tally and stopping probability schedule for round."""

        if len(self.rounds) == 1:
            round_draw = self.rounds[0]
        else:
            round_draw = self.rounds[-1] - self.rounds[-2]

        if self.replacement:
            distribution_round_draw = binom.pmf(range(0, round_draw + 1),
                                                round_draw,
                                                self.contest.winner_prop)
            if len(self.rounds) == 1:
                self.distribution_reported_tally = distribution_round_draw
            else:
                self.distribution_reported_tally = fftconvolve(
                    self.distribution_reported_tally, distribution_round_draw)
        else:
            reported_winner_ballots = int(self.contest.winner_prop *
                                          self.contest.contest_ballots)
            if len(self.rounds) == 1:
                # Simply compute hypergeometric for 1st round distribution
                self.distribution_reported_tally = hypergeom.pmf(
                    np.arange(round_draw + 1), self.contest.contest_ballots,
                    reported_winner_ballots, round_draw)
            else:
                distribution_round_draw = [
                    0 for i in range(self.rounds[-1] + 1)
                ]
                # Get relevant interval of previous round distribution
                interval = self.__get_interval(
                    self.distribution_reported_tally)
                # For every possible number of winner ballots in previous rounds
                # and every possibility in the current round
                # compute probability of their simultaneity
                for prev_round_possibility in range(interval[0],
                                                    interval[1] + 1):
                    unsampled_contest_ballots = self.contest.contest_ballots - self.rounds[-2]
                    unsampled_winner_ballots = reported_winner_ballots - prev_round_possibility

                    curr_round_draw = hypergeom.pmf(np.arange(round_draw + 1),
                                                    unsampled_contest_ballots,
                                                    unsampled_winner_ballots,
                                                    round_draw)
                    for curr_round_possibility in range(round_draw + 1):
                        component_prob = self.distribution_reported_tally[
                            prev_round_possibility] * curr_round_draw[
                                curr_round_possibility]
                        distribution_round_draw[
                            prev_round_possibility +
                            curr_round_possibility] += component_prob
                self.distribution_reported_tally = distribution_round_draw

        self.stopping_prob_schedule.append(
            sum(self.distribution_reported_tally[kmin + 1:]))
        self.distribution_reported_tally = self.distribution_reported_tally[:
                                                                            kmin
                                                                            +
                                                                            1]

    def __get_interval(self, dist):
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

        # Handle the edge case of a small distribution
        if sum(dist) < 2 * tolerance:
            return [int(len(dist) / 2 - 1), int(len(dist) / 2 + 1)]

        interval = [0, len(dist)]
        lower_sum = 0
        upper_sum = 0

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

    def asn(self):
        """Compute ASN as described in BRAVO paper.

        Given the fractional margin for the reported winner and the risk limit (alpha) produce the
        average number of ballots sampled during the audit.

        Returns:
            int: ASN value.
        """
        winner_prop = self.contest.winner_prop
        loser_prop = 1.0 - winner_prop
        margin = (2 * winner_prop) - 1
        z_w = math.log(margin + 1)
        z_l = math.log(1 - margin)
        top = (math.log(1.0/self.alpha) + (z_w / 2.0))
        bottom = (winner_prop * z_w) + (loser_prop * z_l)
        return math.ceil(top / bottom)

    def run(self):
        """Begin interactive audit execution.

        Begins the interactive version of the audit. While computations for different audits will
        vary, the process for executing each one is the same. This provides a process for selecting
        a sample size, determining if the ballots found for the reported winner in that sample
        size meet the stopping condition(s), and if not continuing with the audit. As the audit
        proceeds, data including round sizes, ballots for the winner in each round size, and per
        round risk and stopping probability are stored.
        """

        self.__reset()
        print('Beginning Audit...')
        sample_size = 0
        max_sample_size = self.contest.contest_ballots * self.max_fraction_to_draw
        previous_votes_for_winner = 0

        while sample_size < max_sample_size:
            self.next_sample_size()

            while True:
                sample_size = int(
                    input('Enter next sample size (as a running total): '))
                if sample_size < 1:
                    print('Invalid Input: Sample size must be greater than 1.')
                    continue
                if len(self.rounds) > 0 and sample_size <= self.rounds[-1]:
                    print(
                        'Invalid Input: Sample size must be greater than previous round.'
                    )
                    continue
                if sample_size < self.min_sample_size:
                    print('Invalid Input: Sample size must be larger than ',
                          self.min_sample_size)
                    continue
                if sample_size > max_sample_size:
                    print('Invalid Input: Sample size cannot exceed ',
                          max_sample_size)
                    continue
                break

            while sample_size < 1 or sample_size > max_sample_size:
                print(
                    'Invalid sample size! Please enter a sample size between 1 and ',
                    max_sample_size)
                sample_size = int(
                    input('Enter next sample size (as a running total): '))

            self.rounds.append(sample_size)
            while True:
                votes_for_winner = int(
                    input(
                        'Enter total number of votes for reported winner found in sample: '
                    ))
                if votes_for_winner < 0:
                    print(
                        'Invalid Input: Votes for winner must be non-negative.'
                    )
                    continue
                if votes_for_winner < previous_votes_for_winner:
                    print('Invalid Input: Votes for winner cannot decrease.')
                    continue
                if votes_for_winner > sample_size:
                    print(
                        'Invalid Input: Votes for winner cannot exceed sample size.'
                    )
                    continue
                break

            if self.stopping_condition(votes_for_winner):
                print('Audit Complete: Stopping condition met.')
                return
            else:
                print('Stopping condition not met!!')
                force_stop = input(
                    'Would you like to force stop the audit [y/n]: ')
                if force_stop == 'y':
                    print('Audit Complete: User stopped.')
                    return

            kmin = self.next_min_winner_ballots(sample_size)
            self.min_winner_ballots.append(kmin)
            self.current_dist_null(kmin)
            self.current_dist_reported(kmin)
            previous_votes_for_winner = votes_for_winner
            self.sample_winner_ballots.append(votes_for_winner)

        print('Audit Complete: Reached max sample size.')

    def __reset(self):
        """Reset attributes modified during run()."""

        self.rounds = []
        self.min_winner_ballots = []
        self.sample_winner_ballots = []
        self.risk_schedule = []
        self.stopping_prob_schedule = []
        self.distribution_null = [1.0]
        self.distribution_reported_tally = [1.0]

    @abstractmethod
    def get_min_sample_size(self):
        """Get the smallest valid sample size."""

        pass

    @abstractmethod
    def next_sample_size(self, *args, **kwargs):
        """Generate estimates of possible next sample sizes.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def stopping_condition(self, votes_for_winner: int) -> bool:
        """Determine if the audits stopping condition has been met.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def next_min_winner_ballots(self, sample_size) -> int:
        """Compute next stopping size of given (actual) sample size.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def compute_min_winner_ballots(self, *args, **kwargs):
        """Compute the stopping size(s) for any number of sample sizes."""

        pass

    @abstractmethod
    def compute_all_min_winner_ballots(self, *args, **kwargs):
        """Compute all stopping sizes from the minimum sample size on."""

        pass

    @abstractmethod
    def compute_risk(self, *args, **kwargs):
        """Compute the current risk level of the audit.

        Returns:
            Current risk level of the audit (as defined per audit implementation).
        """

        pass
