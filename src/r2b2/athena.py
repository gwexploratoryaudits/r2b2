"""Athena audit module."""
import math
from typing import List

import click
from scipy.stats import binom

from r2b2.audit import Audit
from r2b2.audit import PairwiseAudit
from r2b2.contest import Contest


class Athena(Audit):
    """Athena audit implementation.

    An Athena audit is a type of risk-limiting audit that accounts for round-by-round auditor
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
    def __init__(self, alpha: float, delta: float, max_fraction_to_draw: float, contest: Contest):
        """Initialize an Athena audit."""
        if delta <= 0:
            raise ValueError("Delta must be > 0.")

        super().__init__(alpha, 0.0, max_fraction_to_draw, True, contest)

        # The delta condition is an additional stopping rule imposed by the Athena (proper) audit,
        # but p-values reported are identical to Minerva. (We do not attempt to amalgamate the
        # Minerva p-value and the BRAVO p-value into a single p-value.)
        self.delta = delta
        for pair, sub_audit in self.sub_audits.items():
            self.sub_audits[pair].min_sample_size = self.get_min_sample_size(sub_audit)

    def get_min_sample_size(self, sub_audit: PairwiseAudit, min_sprob: float = 10**(-6)):
        """Computes the minimum sample size that has a stopping size (kmin). Here we find a
        practical minimum instead of the theoretical minimum (BRAVO's minimum) to avoid
        floating-point imprecisions in the later convolution process.

        Args:
            min_sprob (float): Round sizes with below min_sprob stopping probability are excluded.
        Returns:
            int: The minimum sample size of the audit, adherent to the min_sprob.
        """

        # p0 is not .5 for contests with odd total ballots.
        p0 = (sub_audit.sub_contest.contest_ballots // 2) / sub_audit.sub_contest.contest_ballots
        p1 = sub_audit.sub_contest.winner_prop
        max_sample_size = math.ceil(sub_audit.sub_contest.contest_ballots * self.max_fraction_to_draw)

        # There may not be a point n' such that all n >= n' are acceptable round sizes and all
        # n < n' are unacceptable round sizes.
        for n in range(1, max_sample_size):
            num_dist = binom.pmf(range(n + 1), n, p1)
            denom_dist = binom.pmf(range(n + 1), n, p0)
            if self.satisfactory_sample_size(n // 2, n + 1, min_sprob, num_dist, denom_dist):
                return n

        return max_sample_size

    def satisfactory_sample_size(self, left, right, sprob, num_dist, denom_dist):
        """Helper method that returns True if the round size satisfies the stopping probability."""
        if left >= right:
            return False

        mid = (left + right) // 2

        sum_num = sum(num_dist[mid:])
        sum_denom = sum(denom_dist[mid:])
        satisfies_risk = self.alpha * sum_num > sum_denom and (self.delta * num_dist[mid] > denom_dist[mid]) and sum_denom > 0
        satisfies_sprob = sum_num > sprob

        if satisfies_risk and satisfies_sprob:
            return True
        elif satisfies_risk and not satisfies_sprob:
            return self.satisfactory_sample_size(left, mid - 1, sprob, num_dist, denom_dist)
        elif not satisfies_risk and satisfies_sprob:
            return self.satisfactory_sample_size(mid + 1, right, sprob, num_dist, denom_dist)
        else:
            return False

    def next_sample_size(self, *args, **kwargs):
        pass

    def stopping_condition_pairwise(self, pair: str, verbose: bool = False) -> bool:
        """Check, without finding the kmin, whether the audit is complete."""
        if len(self.rounds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')
        if pair not in self.sub_audits.keys():
            raise ValueError('pair must be a reported pair in a valid subaudit.')

        votes_for_winner = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        tail_null = sum(self.sub_audits[pair].distribution_null[votes_for_winner:])
        tail_reported = sum(self.sub_audits[pair].distribution_reported_tally[votes_for_winner:])
        point_null = self.sub_audits[pair].distribution_null[votes_for_winner]
        point_reported = self.sub_audits[pair].distribution_reported_tally[votes_for_winner]

        # The delta condition does not affect the p-value reported here; this could mean
        # that a p-value < alpha will be reported, yet the audit cannot stop.
        self.sub_audits[pair].pvalue_schedule.append(tail_null / tail_reported)
        if verbose:
            click.echo('\nMinerva p-value: {}'.format(tail_null / tail_reported))

        self.sub_audits[pair].stopped = (self.alpha * tail_reported > tail_null and self.delta * point_reported > point_null)
        return self.sub_audits[pair].stopped

    def next_min_winner_ballots_pairwise(self, sub_audit: PairwiseAudit) -> int:
        """Compute kmin in interactive context."""
        sample_size = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] + self.sample_ballots[
            sub_audit.sub_contest.reported_loser][-1]
        return self.find_kmin(sub_audit, sample_size, False)

    def compute_min_winner_ballots(self, sub_audit: PairwiseAudit, rounds: List[int], *args, **kwargs):
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

        for i in range(len(rounds)):
            if rounds[i] < sub_audit.min_sample_size:
                raise ValueError('Sample size must be >= minimum sample size.')
            if rounds[i] > self.contest.contest_ballots * self.max_fraction_to_draw:
                raise ValueError('Sample size cannot exceed the maximum fraction of contest ballots to draw.')
            if rounds[i] > sub_audit.sub_contest.contest_ballots:
                raise ValueError('Sample size cannot exceed subaudit contest ballots.')
            if i >= 1 and rounds[i] <= rounds[i - 1]:
                raise ValueError('Round schedule is cumulative and so must strictly increase.')

        previous_sample = 0
        pair = sub_audit.get_pair_str()
        for round_size in rounds:
            self.rounds.append(round_size)
            # Compute marginal round size
            sample_size = round_size - previous_sample
            # Update current distributions for pairwise subaudit
            self._current_dist_null_pairwise(pair, sub_audit, True)
            self._current_dist_reported_pairwise(pair, sub_audit, True)
            # Find kmin for pairwise subaudit and append kmin
            self.find_kmin(sub_audit, sample_size, True, pair)
            # Truncate distributions for pairwise subaudit
            self._truncate_dist_null_pairwise(pair)
            self._truncate_dist_reported_pairwise(pair)
            # Update previous round size for next sample computation
            previous_sample = round_size

    def find_kmin(self, sub_audit: PairwiseAudit, sample_size: int, append: bool, loser: str = None):
        """Search for a kmin (minimum number of winner ballots) satisfying all stopping criteria.

        Args:
            append (bool): Optionally append the kmins to the min_winner_ballots list. This may
            not always be desirable here because, for example, appending happens automatically
            outside this method during an interactive audit.
        """

        for possible_kmin in range(sample_size // 2 + 1, len(sub_audit.distribution_null)):
            tail_null = sum(sub_audit.distribution_null[possible_kmin:])
            tail_reported = sum(sub_audit.distribution_reported_tally[possible_kmin:])
            point_null = sub_audit.distribution_null[possible_kmin]
            point_reported = sub_audit.distribution_reported_tally[possible_kmin]

            # Athena's stopping criterion: tail_reported / tail_null > 1 / alpha,
            # and point_reported / point_null > 1 / delta.
            if self.alpha * tail_reported > tail_null and self.delta * point_reported > point_null:
                if append:
                    if loser is None:
                        raise Exception('must specify loser to append kmin.')
                    self.sub_audits[loser].min_winner_ballots.append(possible_kmin)
                return possible_kmin

        # Sentinel of None plays nice with truncation.
        if append:
            if loser is None:
                raise Exception('must specify loser to append kmin.')
            self.sub_audits[loser].min_winner_ballots.append(None)
        return None

    def compute_all_min_winner_ballots(self, sub_audit: PairwiseAudit, max_sample_size: int = None, *args, **kwargs):
        """Compute the minimum number of winner ballots for the complete (that is, ballot-by-ballot)
        round schedule.

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
        if max_sample_size < sub_audit.min_sample_size:
            raise ValueError("Maximum sample size must be greater than or equal to minimum size.")
        if max_sample_size > sub_audit.sub_contest.contest_ballots:
            raise ValueError("Maximum sample size cannot exceed total contest ballots.")

        pair = sub_audit.get_pair_str()
        for sample_size in range(sub_audit.min_sample_size, max_sample_size + 1):
            self.rounds.append(sample_size)
            # First kmin computed directly.
            if sample_size == sub_audit.min_sample_size:
                self._current_dist_null_pairwise(pair, sub_audit, True)
                self._current_dist_reported_pairwise(pair, sub_audit, True)
                current_kmin = self.find_kmin(sub_audit, sample_size, True, pair)
            else:
                self._current_dist_null_pairwise(pair, sub_audit, True)
                self._current_dist_reported_pairwise(pair, sub_audit, True)
                tail_null = sum(sub_audit.distribution_null[current_kmin:])
                tail_reported = sum(sub_audit.distribution_reported_tally[current_kmin:])
                if self.alpha * tail_reported > tail_null:
                    sub_audit.min_winner_ballots.append(current_kmin)
                else:
                    current_kmin += 1
                    sub_audit.min_winner_ballots.append(current_kmin)
            self._truncate_dist_null_pairwise(pair)
            self._truncate_dist_reported_pairwise(pair)

    def compute_risk(self, votes_for_winner: int, loser: str, *args, **kwargs):
        """Return the hypothetical (Minerva) p-value if votes_for_winner were obtained in the most recent
        round."""

        sub_audit = self.sub_audits[loser]
        tail_null = sum(sub_audit.distribution_null[votes_for_winner:])
        tail_reported = sum(sub_audit.distribution_reported_tally[votes_for_winner:])
        return tail_null / tail_reported

    def get_risk_level(self):
        """Return the risk level of an interactive Athena audit. Non-interactive and bulk Athena
        audits are not considered here since the sampled number of reported winner ballots is not
        available.
        """

        if len(self.pvalue_schedule) < 1:
            return None
        return min(self.pvalue_schedule)
