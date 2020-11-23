"""Minerva audit module."""
import math
from typing import List

import click
from scipy.signal import convolve
from scipy.stats import binom
from scipy.stats import norm

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

    def get_min_sample_size(self, min_sprob: float = 10 ** (-6)):
        """Computes the minimum sample size that has a stopping size (kmin). Here we find a
        practical minimum instead of the theoretical minimum (BRAVO's minimum) to avoid
        floating-point imprecisions in the later convolution process.

        Args:
            min_sprob (float): Round sizes with below min_sprob stopping probability are excluded.
        Returns:
            int: The minimum sample size of the audit, adherent to the min_sprob.
        """

        return self.next_sample_size(sprob=min_sprob)

    def satisfactory_sample_size(self, left, right, sprob, num_dist, denom_dist):
        """Helper method that returns True if the round size satisfies the stopping probability."""
        if left > right:
            return False

        mid = (left + right) // 2

        sum_num = sum(num_dist[mid:])
        sum_denom = sum(denom_dist[mid:])
        satisfies_risk = self.alpha * sum_num > sum_denom and sum_denom > 0
        satisfies_sprob = sum_num > sprob

        if satisfies_risk and satisfies_sprob:
            return True
        elif satisfies_risk and not satisfies_sprob:
            return self.satisfactory_sample_size(left, mid - 1, sprob, num_dist, denom_dist)
        elif not satisfies_risk and satisfies_sprob:
            return self.satisfactory_sample_size(mid + 1, right, sprob, num_dist, denom_dist)
        else:
            return False

    def kmin_search_upper_bound(self, n):
        """
        The Minerva kmin is no greater than the BRAVO kmin, so the latter serves
        as an upper bound for a kmin binary search.

        (Solve for k: (p/.5)^k * ((1-p)/.5)^(n-k) > 1/alpha)
        """

        x = (1 - self.contest.winner_prop) / .5
        y = math.log(self.contest.winner_prop / (1 - self.contest.winner_prop))
        return math.ceil((-n * math.log(x) - math.log(self.alpha)) / y)

    def sample_size_kmin(self, left, right, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right):
        """Finds a kmin with a binary search given the twin distributions."""
        if left > right:
            return 0

        mid = (left + right) // 2

        sum_num = sum(num_dist[mid:orig_right]) + sum_num_right
        sum_denom = sum(denom_dist[mid:orig_right]) + sum_denom_right
        satisfies_risk = self.alpha * sum_num > sum_denom

        sum_num_prev = sum_num + num_dist[mid-1]
        sum_denom_prev = sum_denom + denom_dist[mid-1]
        satisfies_risk_prev = self.alpha * (sum_num_prev + 0) > (sum_denom_prev + 0)

        if satisfies_risk and not satisfies_risk_prev:
            return mid
        elif satisfies_risk and satisfies_risk_prev:
            return self.sample_size_kmin(left, mid - 1, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        elif not satisfies_risk and not satisfies_risk_prev:
            return self.sample_size_kmin(mid + 1, right, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        else:
            raise Exception("sample_size_sprob: k not monotonic.")

    def find_sprob(self, n):
        """Helper method to find the stopping probability of a given prospective round size."""
        p0 = (self.contest.contest_ballots // 2) / self.contest.contest_ballots
        p1 = self.contest.winner_prop

        # The number of ballots that will be drawn this round.
        if len(self.rounds) > 0:
            round_draw = n - self.rounds[-1]
        else:
            round_draw = n

        num_dist_round_draw = binom.pmf(range(0, round_draw + 1), round_draw, p1)
        denom_dist_round_draw = binom.pmf(range(0, round_draw + 1), round_draw, p0)
        if len(self.rounds) > 0:
            num_dist = convolve(self.distribution_reported_tally, num_dist_round_draw, method='fft')
            denom_dist = convolve(self.distribution_null, denom_dist_round_draw, method='fft')
        else:
            num_dist = num_dist_round_draw
            denom_dist = denom_dist_round_draw

        # We find the kmin for this would-be round size.
        right = min(self.kmin_search_upper_bound(n), len(num_dist))
        kmin = self.sample_size_kmin(len(num_dist) // 2, right, num_dist, denom_dist, sum(num_dist[right:]),
                                     sum(denom_dist[right:]), right)

        # If there isn't a kmin, clearly we need a larger round size.
        if kmin == 0:
            return 0, 0.0

        # For the audit to stop, we need to get kmin winner ballots minus the winner ballots we already have.
        if len(self.rounds) > 0:
            needed = kmin - self.sample_winner_ballots[-1]
        else:
            needed = kmin

        # What are the odds that we get as many winner ballots in the round draw
        # as are needed? That is the stopping probability.
        sprob_round = sum(num_dist_round_draw[needed:])

        return kmin, sprob_round

    def binary_search_estimate(self, left, right, sprob):
        """Method to use binary search approximation to find a round size estimate."""

        # An additional check to ensure proper input.
        if left > right:
            return 0, 0, 0.0

        mid = (left + right) // 2

        sprob_kmin_pair = self.find_sprob(mid)

        # This round size is returned if it has satisfactory stopping probability and a round size one less
        # does not, or if it has satisfactory stopping probability and exceeds the desired stopping probability
        # only nominally.
        if right - left <= 1:
            if (sprob_kmin_pair[1] >= sprob):
                assert sprob_kmin_pair[0] > 0
                return mid, sprob_kmin_pair[0], sprob_kmin_pair[1]
            else:
                right_sprob_kmin_pair = self.find_sprob(mid + 1)
                if right_sprob_kmin_pair[1] >= sprob:
                    return mid + 1, self.find_sprob(mid + 1)[0], self.find_sprob(mid + 1)[1]

            return 0, 0, 0.0

        if sprob_kmin_pair[1] >= sprob:
            return self.binary_search_estimate(left, mid, sprob)
        else:
            return self.binary_search_estimate(mid, right, sprob)

    def next_sample_size_gaussian(self, sprob=.9):
        """This is a rougher but quicker round size estimate for very narrow margins."""
        z_a = norm.isf(sprob)
        z_b = norm.isf(self.alpha * sprob)
        p = self.contest.winner_prop
        return math.ceil(((z_a * math.sqrt(p * (1 - p)) - .5 * z_b) / (p - .5)) ** 2)

    def next_sample_size(self, sprob=.9, verbose=False, *args, **kwargs):
        """
        Attempt to find a next sample size estimate no greater than 10000.
        Failing that, try to find an estimate no greater than 20000, and so on.

        Args:
            verbose (bool): If true, the kmin and stopping probability of the next sample size will be returned
            in addition to the next sample size itself.
        """

        # If the audit has already terminated, there is no next_sample_size.
        if len(self.min_winner_ballots) > 0 and self.sample_winner_ballots[-1] >= self.min_winner_ballots[-1]:
            if verbose:
                return self.rounds[-1], 0, 1
            return self.rounds[-1]

        # NOTE: Numerical issues arise when sample results disagree to an extreme extent with the reported margin.
        start = 10000
        if len(self.rounds) > 0:
            init_upper_bound = self.get_upper_bound(self.rounds[-1] + 1, start)
        else:
            init_upper_bound = start
        upper_bound = init_upper_bound
        while upper_bound < 10 ** 7:
            if len(self.rounds) > 0:
                # Ensure upper bound is sufficiently large.
                if upper_bound == init_upper_bound:
                    estimate = self.binary_search_estimate(self.rounds[-1] + 1, upper_bound, sprob)
                else:
                    estimate = self.binary_search_estimate(upper_bound // 2, upper_bound, sprob)
            else:
                if upper_bound == init_upper_bound:
                    estimate = self.binary_search_estimate(1, upper_bound, sprob)
                else:
                    estimate = self.binary_search_estimate(upper_bound // 2, upper_bound, sprob)
            if estimate[0] > 0:
                if verbose:
                    return estimate
                return estimate[0]
            upper_bound *= 2
        return 0

    def get_upper_bound(self, n, start):
        while start <= n:
            start *= 2
        return start

    def stopping_condition(self, votes_for_winner: int, verbose: bool = False) -> bool:
        """Check, without finding the kmin, whether the audit is complete."""
        if len(self.rounds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')

        tail_null = sum(self.distribution_null[votes_for_winner:])
        tail_reported = sum(self.distribution_reported_tally[votes_for_winner:])

        pvalue = self.compute_risk(votes_for_winner)
        self.pvalue_schedule.append(pvalue)
        if verbose:
            click.echo('\np-value: {}'.format(pvalue))
            click.echo('\nRisk Level: {}'.format(self.get_risk_level()))

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

        for i in range(len(rounds)):
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

    def compute_risk(self, votes_for_winner: int, *args, **kwargs):
        """Return the hypothetical pvalue if votes_for_winner were obtained in the most recent
        round."""

        tail_null = sum(self.distribution_null[votes_for_winner:])
        tail_reported = sum(self.distribution_reported_tally[votes_for_winner:])

        if tail_reported == 0:
            return 0
        return tail_null / tail_reported

    def get_risk_level(self):
        """Return the risk level of an interactive Minerva audit. Non-interactive and bulk Minerva
        audits are not considered here since the sampled number of reported winner ballots is not
        available.
        """

        if len(self.pvalue_schedule) < 1:
            return None
        return min(self.pvalue_schedule)
