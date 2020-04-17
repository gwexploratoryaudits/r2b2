"""Bayesian Risk-Limiting Audit module."""
import math
from typing import List

import numpy as np

from r2b2.audit import Audit
from r2b2.contest import Contest


class BayesianRLAReplace(Audit):
    """Baysian Risk-Limiting Audit implementation.

    A Bayesian Risk-Limit Audit with Replacement implementation as defined by Vora, et. al. for auditing 2-candidate
    plurality elections. For a given sample size, the audit software calculates a minimum number of
    votes for the reported winner that must be found in the sample to stop the audit and confirm
    the reported outcome.

    Attributes:
        alpha (float): Risk limit. Alpha represents the chance, that given an incorrectly called
            election, the audit will fail to force a full recount.
        max_fraction_to_draw (int): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        rounds (List[int]): The round sizes used during the audit.
        min_winner_ballots (List[int]): Stopping sizes precomputed for each of the given round
            sizes.
        contest (Contest): Contest to be audited.
        prior (np.ndarray): Prior distribution for worst-case election.
    """

    prior: np.ndarray

    def __init__(self, alpha: float, max_fraction_to_draw: float,
                 contest: Contest):
        """Initialize a Bayesian RLA."""

        super().__init__(alpha, 0.0, max_fraction_to_draw, False, contest)
        self.prior = self.compute_prior()
        self.min_sample_size = self.get_min_sample_size()

    def get_min_sample_size(self):
        left = 1
        right = math.ceil(self.contest.contest_ballots *
                          self.max_fraction_to_draw)

        while left < right:
            proposed_min = (left + right) // 2
            proposed_min_kmin = self.next_min_winner_ballots(proposed_min)

            if proposed_min_kmin == -1:
                left = proposed_min + 1
            else:
                previous_kmin = self.next_min_winner_ballots(proposed_min - 1)
                if previous_kmin == -1:
                    return proposed_min
                else:
                    right = proposed_min - 1
        # FIXME: need check for final size, if we reach this is the contest to small for the audit?
        return left

    def stopping_condition(self, votes_for_winner: int) -> bool:
        if len(self.rounds) < 1:
            raise Exception(
                'Attempted to call stopping condition without any rounds.')
        return self.compute_risk(votes_for_winner,
                                 self.rounds[-1]) <= self.alpha

    def next_min_winner_ballots(self, sample_size: int) -> int:
        """Compute the stopping size requirement for a given round.

        Args:
            sample_size (int): Current round size, i.e. number of ballots to be sampled in round

        Returns:
            int: The minimum number of votes cast for the reported winner in the
            current round size in order to stop the audit during that round. -1 if
            the sample_size is invalid.
        """

        if sample_size < self.min_sample_size:
            return -1

        left = math.floor(sample_size / 2)
        right = sample_size

        while left < right:
            proposed_stop = (left + right) // 2
            proposed_stop_risk = self.compute_risk(proposed_stop, sample_size)

            if proposed_stop_risk == self.alpha:
                return proposed_stop

            if proposed_stop_risk < self.alpha:
                previous_stop_risk = self.compute_risk(proposed_stop - 1,
                                                       sample_size)
                if previous_stop_risk == self.alpha:
                    return proposed_stop - 1
                if previous_stop_risk > self.alpha:
                    return proposed_stop
                right = proposed_stop - 1
            else:
                left = proposed_stop + 1

        # Handle case where kmin = sample_size
        proposed_stop_risk = self.compute_risk(sample_size, sample_size)
        if proposed_stop_risk <= self.alpha:
            return sample_size
        # Otherwise kmin > sample_size, so we return -1
        return -1

    def compute_prior(self) -> np.ndarray:
        """Compute prior distribution of worst case election."""

        half_contest_ballots = math.floor(self.contest.contest_ballots / 2)
        left = np.zeros(half_contest_ballots, dtype=float)
        mid = np.array([0.5])
        right = np.array([
            (0.5 / float(half_contest_ballots))
            for i in range(self.contest.contest_ballots - half_contest_ballots)
        ],
                         dtype=float)
        return np.concatenate((left, mid, right))

    def compute_risk(self,
                     votes_for_winner: int = None,
                     current_round: int = None,
                     *args,
                     **kwargs) -> float:
        """Compute the risk level given current round size and votes for winner in sample

        The risk level is computed using the normalized product of the prior and posterior
        distributions. The prior comes from compute_prior() and the posterior is the binomial
        distribution of finding votes_for_winner from a sample of size current_round taken from a
        total size of contest_ballots. The risk is defined as the lower half of the distribution,
        i.e. the portion of the distribution associated with an incorrectly reported outcome.

        Args:
            votes_for_winner (int): Votes found for reported winner in current round size.
            current_round(int): Current round size.

        Returns:
            float: Value for risk of given sample and round size.
        """

        N = self.contest.contest_ballots
        posterior = np.array([
            np.power(x / N, votes_for_winner) * np.power(1 - x / N, current_round - votes_for_winner)
            for x in range(N + 1)
        ])
        posterior = self.prior * posterior
        normalize = sum(posterior)
        if normalize > 0:
            posterior = posterior / normalize

        return sum(posterior[range(math.floor(self.contest.contest_ballots / 2)+1)])

    def next_sample_size(self):
        # TODO: Documentation
        # TODO: Implement
        pass

    def compute_min_winner_ballots(self, rounds: List[int], *args, **kwargs):
        """Compute the minimum number of winner ballots for a list of round sizes.

        Compute a list of minimum number of winner ballots that must be found in the
        corresponding round (sample) sizes to meet the stopping condition.

        Args:
            rounds (List[int]): List of round sizes.

        Returns:
            List[int]: List of minimum winner ballots to meet the stopping conditions for each
            round size in rounds.
        """

        if len(rounds) < 1:
            raise ValueError('rounds must contain at least 1 round size.')
        previous_round = 0
        for sample_size in rounds:
            if sample_size < 1:
                raise ValueError('Sample size must be at least 1.')
            if sample_size > self.contest.contest_ballots * self.max_fraction_to_draw:
                raise ValueError(
                    'Sample size cannot be larger than max fraction to draw of the contest ballots.'
                )
            if sample_size <= previous_round:
                raise ValueError('Sample sizes must be in increasing order.')
            previous_round = sample_size

        self.rounds = rounds
        min_winner_ballots = []
        for sample_size in self.rounds:
            min_winner_ballots.append(
                self.next_min_winner_ballots(sample_size))

        return min_winner_ballots

    def compute_all_min_winner_ballots(self,
                                       max_sample_size: int = None,
                                       *args,
                                       **kwargs):
        """Compute the minimum winner ballots for all possible sample sizes.

        Args:
            max_sample_size (int): Optional. Set maximum sample size to generate stopping sizes up
                to. If not provided the maximum sample size is determined by max_fraction_to_draw
                and the total contest ballots.

        Returns:
            List[int]: List of minimum winner ballots to meet the stopping condition for each round
                size in the range [min_sample_size, max_sample_size].
        """

        if max_sample_size is None:
            max_sample_size = math.ceil(self.contest.contest_ballots *
                                        self.max_fraction_to_draw)
        if max_sample_size < self.min_sample_size:
            raise ValueError(
                'Maximum sample size must be greater than or equal to minimum size.'
            )
        if max_sample_size > self.contest.contest_ballots:
            raise ValueError(
                'Maximum sample size cannot exceed total contest ballots.')

        current_kmin = self.next_min_winner_ballots(self.min_sample_size)
        min_winner_ballots = [current_kmin]

        # For each additional ballot, the kmin can only increase by
        for sample_size in range(self.min_sample_size + 1,
                                 max_sample_size + 1):
            if self.compute_risk(current_kmin, sample_size) > self.alpha:
                current_kmin += 1

            min_winner_ballots.append(current_kmin)

        return min_winner_ballots
