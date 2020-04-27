"""Minerva audit module."""
import math
from typing import List

from r2b2.audit import Audit
from r2b2.contest import Contest


class Minerva(Audit):
    """Minerva audit implementation.

    A Minerva audit is a type of risk-limiting audit that accounts for round-by-round auditor
    decisions. For a given sample size (in the context of a round schedule), the audit software
    calculates a minimum number of votes for the reported winner that must be found in the sample
    to stop the audit and confirm the reported outcome.

    Attributes:
        alpha (float): Risk limit. Alpha represents the chance that, given an incorrectly called
        election, the audit will fail to force a full recount.
        max_fraction_to_draw (float): The maximum number of ballots the auditors are willing to draw
        as a fraction of the ballots in the contest.
        rounds (List[int]): Cumulative round schedule.
        min_winner_ballots (List[int]): Stopping sizes (or kmins) respective to the round schedule.
        contest (Contest): Contest to be audited.
    """

    def __init__(self, alpha: float, max_fraction_to_draw: float, contest: Contest):
        """Initialize a Minerva audit."""
        super().__init__(alpha, 0.0, max_fraction_to_draw, True, contest)
        self.min_sample_size = self.get_min_sample_size()
        self.rounds = []
        self.min_winner_ballots = []

    def get_min_sample_size(self):
        """Computes the minimum sample size that has a stopping size (kmin).

        Returns:
            int: The minimum sample size of the audit.
        """

        # TODO: Implement "meaningful minimum" sample size, perhaps with tolerance 10^-18.

        # p0 is not .5 for contests with odd total ballots.
        p0 = (self.contest.contest_ballots // 2) / self.contest.contest_ballots

        num = math.log(1 / self.alpha)
        denom = math.log(self.contest.winner_prop / p0)

        return math.ceil(num / denom)

    def next_sample_size(self, *args, **kwargs):
        pass

    def stopping_condition(self, votes_for_winner: int) -> bool:
        # NOTE: Before computation of kmin.
        pass

    def next_min_winner_ballots(self, sample_size) -> int:
        pass

    def compute_min_winner_ballots(self, rounds: List[int], *args, **kwargs):
        """Compute the minimum number of winner ballots for a round schedule.

        Extend the audit's round schedule with the passed (partial) round schedule, and then extend
        the audit's minimum number of winner ballots schedule with the corresponding minimums to
        meet the stopping condition.

        Args: rounds (List[int]): A (partial) round schedule of the audit.
        """

        if len(rounds) < 1:
            raise ValueError('Round schedule must contain at least 1 round.')

        if len(self.rounds) > 0 and rounds[0] <= self.rounds[-1]:
            raise ValueError('Sample sizes must exceed past sample sizes.')

        for i in range(0, len(rounds)):
            if rounds[i] < self.min_sample_size:
                raise ValueError('Sample size must be >= minimum sample size.')
            if rounds[i] > self.contest.contest_ballots * self.max_fraction_to_draw:
                raise ValueError(
                    'Sample size cannot exceed the maximum fraction of contest ballots to draw.')
            if i >= 1 and rounds[i] <= rounds[i - 1]:
                raise ValueError('Round schedule is cumulative and so must strictly increase.')

        for sample_size in rounds:
            self.rounds.append(sample_size)
            self.current_dist_null()
            self.current_dist_reported()
            self.find_kmin()
            self.truncate_dist_null()
            self.truncate_dist_reported()

    def find_kmin(self):
        """Search for a kmin (minimum number of winner ballots) satisfying all stopping criteria."""

        for possible_kmin in range(self.rounds[-1] // 2 + 1, len(self.distribution_null)):
            tail_null = sum(self.distribution_null[possible_kmin:])
            tail_reported = sum(self.distribution_reported_tally[possible_kmin:])

            # Minerva's stopping criterion: tail_reported / tail_null > 1 / alpha.
            if self.alpha * tail_reported >= tail_null:
                self.min_winner_ballots.append(possible_kmin)
                return

        # Sentinel of None plays nice with truncation.
        self.min_winner_ballots.append(None)

    def compute_all_min_winner_ballots(self, *args, **kwargs):
        pass

    def compute_risk(self, *args, **kwargs):
        # NOTE: For interactive: minimum of 1/ratio (where numerator is realized ballots for winner)
        # schedule. For non-interactive/bulk: possibly the same?. No ratio schedule field here yet.
        pass
