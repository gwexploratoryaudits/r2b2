"""Bayesian Risk-Limiting Audit module."""
from typing import List

import numpy as np
from scipy.stats import hypergeom as hg

from r2b2.audit import Audit
from r2b2.contest import Contest


class BayesianRLA(Audit):
    """Baysian Risk-Limiting Audit implementation.

    A Bayesian Risk-Limit Audit implementation as defined by Vora, et. al. for auditing 2-candidate
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

    def __init__(self, alpha: float, max_fraction_to_draw: float, contest: Contest):
        """Initialize a Bayesian RLA."""

        super().__init__(alpha, 0.0, max_fraction_to_draw, False, contest)
        self.prior = self.compute_prior()

    def stopping_condition(self, votes_for_winner: int) -> bool:
        if len(self.rouunds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')
        return self.compute_risk(votes_for_winner,
                                 self.rounds[-1]) <= self.alpha

    def next_min_winner_ballots(self, sample_size: int) -> int:
        """Compute the stopping size requirement for a given round.

        Args:
            sample_size (int): Current round size, i.e. number of ballots to be sampled in round

        Returns:
            An int which represents the minimum number of votes cast for the reported winner in the
            current round size in order to stop the audit during that round.
        """

        if sample_size < 1:
            raise ValueError('Sample size must be at least 1.')
        if sample_size > self.contest.contest_ballots * self.max_fraction_to_draw:
            raise ValueError('Sample size cannot be larger than max fraction to draw of the contest ballots.')

        left = sample_size // 2
        right = sample_size

        while left < right:
            proposed_stop = (left + right) // 2
            proposed_stop_risk = self.compute_risk(proposed_stop,
                                                   sample_size)

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

        # FIXME: Should we test final size when left = right and return some default if
        # round size is too small?
        return left

    def compute_prior(self) -> np.ndarray:
        """Compute prior distribution of worst case election."""

        left = np.zeros(self.contest.contest_ballots // 2, dtype=float)
        mid = np.array([0.5])
        right = np.array([(0.5 / float(self.contest.contest_ballots // 2))
                          for i in range(self.contest.contest_ballots // 2)],
                         dtype=float)
        return np.concatenate((left, mid, right))

    def compute_risk(self,
                     votes_for_winner: int = None,
                     current_round: int = None,
                     *args,
                     **kwargs) -> float:
        """Compute the risk level given current round size and votes for winner in sample

        The risk level is computed using the normalized product of the prior and posterior
        distributions. The prior comes from compute_prior() and the posterior is the hypergeometric
        distribution of finding votes_for_winner from a sample of size current_round taken from a
        total size of contest_ballots. The risk is defined as the lower half of the distribution,
        i.e. the portion of the distribution associated with an incorrectly reported outcome.

        Args:
            sample (int): Votes found for reported winner in current round size.
            current_round(int): Current round size.

        Returns:
            float: Value for risk of given sample and round size.
        """

        posterior = np.array([
            hg.pmf(votes_for_winner, self.contest.contest_ballots, x,
                   current_round)
            for x in range(self.contest.contest_ballots + 1)
        ])
        posterior = self.prior * posterior
        normalize = sum(posterior)
        if normalize > 0:
            posterior = posterior / normalize

        return sum(posterior[range(self.contest.contest_ballots // 2 + 1)])

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
                raise ValueError('Sample size cannot be larger than max fraction to draw of the contest ballots.')
            if sample_size <= previous_round:
                raise ValueError('Sample sizes must be in increasing order.')
            previous_round = sample_size

        self.rounds = rounds
        min_winner_ballots = []
        for sample_size in self.rounds:
            min_winner_ballots.append(self.next_min_winner_ballots(sample_size))

        return min_winner_ballots
