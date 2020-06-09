"""Minerva audit module."""
import math
from typing import List

import click

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
        self.realized_risks = []

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

    def stopping_condition(self, votes_for_winner: int, verbose: bool = False) -> bool:
        """Check, without finding the kmin, whether the audit is complete."""
        if len(self.rounds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')

        tail_null = sum(self.distribution_null[votes_for_winner:])
        tail_reported = sum(self.distribution_reported_tally[votes_for_winner:])

        if verbose:
            click.echo('\np-value: {}'.format(tail_null / tail_reported))
        self.realized_risks.append(tail_null / tail_reported)

        return self.alpha * tail_reported > tail_null

    def next_min_winner_ballots(self, sample_size) -> int:
        """Compute kmin in interactive context."""
        return self.find_kmin(False)

    def compute_min_winner_ballots(self, rounds: List[int], *args, **kwargs):
        """Compute the minimum number of winner ballots for a round schedule.

        Extend the audit's round schedule with the passed (partial) round schedule, and then extend
        the audit's minimum number of winner ballots schedule with the corresponding minimums to
        meet the stopping condition.

        Args:
            rounds (List[int]): A (partial) round schedule of the audit.
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
            self.find_kmin(True)
            self.truncate_dist_null()
            self.truncate_dist_reported()

    def find_kmin(self, append: bool):
        """Search for a kmin (minimum number of winner ballots) satisfying all stopping criteria.

        Args:
            append (bool): Optionally append the kmins to the min_winner_ballots list. This may
            not always be desirable here because, for example, appending happens automatically
            outside this method during an interactive audit.
        """

        for possible_kmin in range(self.rounds[-1] // 2 + 1, len(self.distribution_null)):
            tail_null = sum(self.distribution_null[possible_kmin:])
            tail_reported = sum(self.distribution_reported_tally[possible_kmin:])

            # Minerva's stopping criterion: tail_reported / tail_null > 1 / alpha.
            if self.alpha * tail_reported > tail_null:
                if append:
                    self.min_winner_ballots.append(possible_kmin)
                return possible_kmin

        # Sentinel of None plays nice with truncation.
        if append:
            self.min_winner_ballots.append(None)
        return None

    def compute_all_min_winner_ballots(self, max_sample_size: int = None, *args, **kwargs):
        """Compute the minimum number of winner ballots for the complete (that is, ballot-by-ballot)
        round schedule. Note that Minerva ballot-by-ballot is equivalent to the BRAVO audit.

        Note: Due to limited convolutional precision, results may be off somewhat after the
        stopping probability very nearly equals 1.

        Args:
            max_sample_size (int): Optionally set the maximum sample size to generate stopping sizes
            (kmins) up to. If not provided the maximum sample size is determined by max_frac_to_draw
            and the total contest ballots.

        Returns:
            None, kmins are appended to the min_winner_ballots list.
        """

        if len(self.rounds) > 0:
            raise Exception("This audit already has an (at least partial) round schedule.")
        if max_sample_size is None:
            max_sample_size = math.ceil(self.contest.contest_ballots * self.max_fraction_to_draw)
        if max_sample_size < self.min_sample_size:
            raise ValueError("Maximum sample size must be greater than or equal to minimum size.")
        if max_sample_size > self.contest.contest_ballots:
            raise ValueError("Maximum sample size cannot exceed total contest ballots.")

        for sample_size in range(self.min_sample_size, max_sample_size + 1):
            self.rounds.append(sample_size)
            self.current_dist_null()
            self.current_dist_reported()
            # First kmin computed directly.
            if sample_size == self.min_sample_size:
                current_kmin = self.find_kmin(True)
            else:
                tail_null = sum(self.distribution_null[current_kmin:])
                tail_reported = sum(self.distribution_reported_tally[current_kmin:])
                if self.alpha * tail_reported > tail_null:
                    self.min_winner_ballots.append(current_kmin)
                else:
                    current_kmin += 1
                    self.min_winner_ballots.append(current_kmin)
            self.truncate_dist_null()
            self.truncate_dist_reported()

    def compute_risk(self, *args, **kwargs):
        """Return the current risk level of an interactive Minerva audit. Non-interactive and bulk
        Minerva audits are not considered here since the sampled number of reported winner ballots
        is not available.
        """

        if len(self.realized_risks) < 1:
            return None
        return min(self.realized_risks)
