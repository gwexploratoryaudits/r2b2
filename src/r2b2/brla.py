"""Bayesian Risk-Limiting Audit module."""
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
        return self.compute_risk(votes_for_winner,
                                 self.rounds[-1]) <= self.alpha

    def next_min_winner_ballots(self, sample_size: int) -> int:
        return self.compute_min_winner_ballots(sample_size)

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

    def compute_min_winner_ballots(self, current_round: int, *args, **kwargs):
        """Compute the stopping size requirement for a given round.

        Args:
            current_round (int): Current round size, i.e. number of ballots to be sampled in round

        Returns:
            An int which represents the minimum number of votes cast for the reported winner in the
            current round size in order to stop the audit during that round.

        Raises:
            ValueError: The current round size is not one of the audits rounds.
        """

        if current_round not in self.rounds:
            raise ValueError("Invalid round size.")

        left = current_round // 2
        right = current_round

        while left < right:
            proposed_stop = (left + right) // 2
            proposed_stop_risk = self.compute_risk(proposed_stop,
                                                   current_round)

            if proposed_stop_risk == self.alpha:
                return proposed_stop

            if proposed_stop_risk < self.alpha:
                previous_stop_risk = self.compute_risk(proposed_stop - 1,
                                                       current_round)
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
