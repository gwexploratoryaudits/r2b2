from typing import Dict
from typing import List

import numpy as np
from scipy.stats import hypergeom as hg

from r2b2.audit import Audit


class BayesianRLA(Audit):
    """Baysian Risk-Limiting Audit implementation.

    A Bayesian Risk-Limit Audit implementation as defined by Vora, et. al. for auditing 2-candidate
    plurailty elections. For a given set of rounds, the audit software provides a minimum number of
    votes for the reported winner that must be found in a round of sampling to stop the audit and
    confirm the reported outcome.

    Attributes:
        alpha (float): Risk limit. Alpha represents the chance, that gien and incorrect called
            election, the audit will fail to force a full recount.
        max_to_draw (int): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        rounds (List[int]): The round sizes to use during the audit.
        prior (np.ndarray): Prior distribution for worst-case election.
        stopping_size (Dict[int, int]): Stopping sizes precomputed for each of the given round
            sizes.
    """

    rounds: List[int]
    stopping_size: Dict[int, int]

    def __init__(self, alpha, max_to_draw, contest, rounds=None, num_rounds=None):
        """Initialize a Byasian RLA."""

        super().__init__(alpha, 0, max_to_draw, False, contest)
        if rounds is not None:
            self.rounds = rounds
        elif num_rounds is not None:
            self.rounds = self.compute_sample_size(num_rounds)
        else:
            self.rounds = self.compute_sample_size(2)
        self.prior = self.compute_prior()
        self.stopping_size = {}
        for i in range(len(self.rounds)):
            self.stopping_size[rounds[i]] = self.compute_stopping_size(
                rounds[i])

    def compute_prior(self):
        """Compute prior distribution of worst case election."""

        left = np.zeros(self.contest.total_ballots_cast // 2, dtype=float)
        mid = np.array([0.5])
        right = np.array(
            [(0.5 / float(self.contest.total_ballots_cast // 2))
             for i in range(self.contest.total_ballots_cast // 2)],
            dtype=float)
        return np.concatenate((left, mid, right))

    def compute_risk(self, sample: int, current_round: int):
        """Compute the risk level given current round size and votes for winner in sample

        TODO: insert description

        Args:
            sample (int): Votes found for reported winner in current round size.
            current_round(int): Current round size.

        Returns:
            Float value for risk of given sample and round size.
        """

        posterior = np.array([
            hg.pmf(sample, self.contest.total_ballots_cast, x, current_round)
            for x in range(self.contest.total_ballots_cast + 1)
        ])
        posterior = self.prior * posterior
        normalize = sum(posterior)
        if normalize > 0:
            posterior = posterior / normalize

        return sum(posterior[range(self.contest.total_ballots_cast // 2 + 1)])

    def compute_sample_size(self, num_rounds: int):
        """Compute list of round sizes for a given number of rounds.

        Returns:
            List of integer round sizes of length num_rounds.
        """
        # TODO: Implement.
        pass

    def compute_stopping_size(self, current_round: int):
        """Compute the stopping size requirement for a given round.

        Args:
            current_round (int): Current round size, i.e. number of ballots to be sampled in round

        Returns:
            An int which represents the minimum number of votes cast for the reported winner in the
            current tound size in order to stop the audit during that round.

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

    def lookup_table(self):
        """Generate a lookup table of stopping values for each round."""

        print('| Rounds   | Stop     |')
        print('|----------|----------|')
        for round_size, stop_size in self.stopping_size.items():
            print('|{:10}|{:10}|'.format(round_size, stop_size))
