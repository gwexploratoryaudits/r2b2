"""Minerva audit module."""
import math

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
        pass

    def next_min_winner_ballots(self, sample_size) -> int:
        pass

    def compute_min_winner_ballots(self, *args, **kwargs):
        pass

    def compute_all_min_winner_ballots(self, *args, **kwargs):
        pass

    def compute_risk(self, *args, **kwargs):
        pass
