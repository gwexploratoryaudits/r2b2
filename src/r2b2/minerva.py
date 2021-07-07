"""Minerva audit module."""
import math
from typing import List

import click
from scipy.signal import convolve
from scipy.stats import binom
from scipy.stats import norm

from r2b2.audit import Audit
from r2b2.audit import PairwiseAudit
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
        contest (Contest): Contest to be audited.
    """
    def __init__(self, alpha: float, max_fraction_to_draw: float, contest: Contest):
        """Initialize a Minerva audit."""
        super().__init__(alpha, 0.0, max_fraction_to_draw, True, contest)
        for pair, sub_audit in self.sub_audits.items():
            self.sub_audits[pair].min_sample_size = self.get_min_sample_size(sub_audit)

    def get_min_sample_size(self, sub_audit: PairwiseAudit, min_sprob: float = 10**(-6)):
        """Computes the minimum sample size that has a stopping size (kmin). Here we find a
        practical minimum instead of the theoretical minimum (BRAVO's minimum) to avoid
        floating-point imprecisions in the later convolution process.

        Args:
            sub_audit (PairwiseAudit): Get minimum sample size for this subaudit.
            min_sprob (float): Round sizes with below min_sprob stopping probability are excluded.

        Returns:
            int: The minimum sample size of the audit, adherent to the min_sprob.
        """

        return self._next_sample_size_pairwise(sub_audit, sprob=min_sprob)[0]

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

    def kmin_search_upper_bound(self, n, sub_audit: PairwiseAudit):
        """
        The Minerva kmin is no greater than the BRAVO kmin, so the latter serves
        as an upper bound for a kmin binary search.

        (Solve for k: (p/.5)^k * ((1-p)/.5)^(n-k) > 1/alpha)
        """

        x = (1 - sub_audit.sub_contest.winner_prop) / .5
        y = math.log(sub_audit.sub_contest.winner_prop / (1 - sub_audit.sub_contest.winner_prop))
        return math.ceil((-n * math.log(x) - math.log(self.alpha)) / y)

    def sample_size_kmin(self, left, right, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right):
        """Finds a kmin with a binary search given the twin distributions."""
        if left > right:
            return 0

        mid = (left + right) // 2

        sum_num = sum(num_dist[mid:orig_right]) + sum_num_right
        sum_denom = sum(denom_dist[mid:orig_right]) + sum_denom_right
        satisfies_risk = self.alpha * sum_num > sum_denom

        sum_num_prev = sum_num + num_dist[mid - 1]
        sum_denom_prev = sum_denom + denom_dist[mid - 1]
        satisfies_risk_prev = self.alpha * (sum_num_prev) > (sum_denom_prev)

        if satisfies_risk and not satisfies_risk_prev:
            return mid
        elif satisfies_risk and satisfies_risk_prev:
            return self.sample_size_kmin(left, mid - 1, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        elif not satisfies_risk and not satisfies_risk_prev:
            return self.sample_size_kmin(mid + 1, right, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        else:
            raise Exception("sample_size_sprob: k not monotonic.")

    def find_sprob(self, n, sub_audit: PairwiseAudit):
        """Helper method to find the stopping probability of a given prospective round size."""
        p0 = (sub_audit.sub_contest.contest_ballots // 2) / sub_audit.sub_contest.contest_ballots
        p1 = sub_audit.sub_contest.winner_prop

        # The number of ballots that will be drawn this round.
        if len(self.rounds) > 0:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots
            round_draw = n - previous_round
        else:
            round_draw = n

        num_dist_round_draw = binom.pmf(range(0, round_draw + 1), round_draw, p1)
        denom_dist_round_draw = binom.pmf(range(0, round_draw + 1), round_draw, p0)
        if len(self.rounds) > 0:
            num_dist = convolve(sub_audit.distribution_reported_tally, num_dist_round_draw, method='direct')
            denom_dist = convolve(sub_audit.distribution_null, denom_dist_round_draw, method='direct')
            num_dist = [abs(p) for p in num_dist]
            denom_dist = [abs(p) for p in denom_dist]
        else:
            num_dist = num_dist_round_draw
            denom_dist = denom_dist_round_draw

        # We find the kmin for this would-be round size.
        right = min(self.kmin_search_upper_bound(n, sub_audit), len(num_dist))
        kmin = self.sample_size_kmin(len(num_dist) // 2, right, num_dist, denom_dist, sum(num_dist[right:]), sum(denom_dist[right:]), right)

        # If there isn't a kmin, clearly we need a larger round size.
        if kmin == 0:
            return 0, 0.0

        # For the audit to stop, we need to get kmin winner ballots minus the winner ballots we already have.
        if len(self.rounds) > 0:
            needed = kmin - self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
        else:
            needed = kmin

        # What are the odds that we get as many winner ballots in the round draw
        # as are needed? That is the stopping probability.
        sprob_round = sum(num_dist_round_draw[needed:])

        return kmin, sprob_round

    def binary_search_estimate(self, left, right, sprob, sub_audit: PairwiseAudit):
        """Method to use binary search approximation to find a round size estimate."""

        # An additional check to ensure proper input.
        if left > right:
            return 0, 0, 0.0

        mid = (left + right) // 2

        sprob_kmin_pair = self.find_sprob(mid, sub_audit)

        # This round size is returned if it has satisfactory stopping probability and a round size one less
        # does not, or if it has satisfactory stopping probability and exceeds the desired stopping probability
        # only nominally.
        if right - left <= 1:
            if (sprob_kmin_pair[1] >= sprob):
                assert sprob_kmin_pair[0] > 0
                return mid, sprob_kmin_pair[0], sprob_kmin_pair[1]
            else:
                right_sprob_kmin_pair = self.find_sprob(mid + 1, sub_audit)
                if right_sprob_kmin_pair[1] >= sprob:
                    return mid + 1, self.find_sprob(mid + 1, sub_audit)[0], self.find_sprob(mid + 1, sub_audit)[1]

            return 0, 0, 0.0

        if sprob_kmin_pair[1] >= sprob:
            return self.binary_search_estimate(left, mid, sprob, sub_audit)
        else:
            return self.binary_search_estimate(mid, right, sprob, sub_audit)

    def next_sample_size_gaussian(self, sprob=.9):
        """This is a rougher but quicker round size estimate for very narrow margins."""
        z_a = norm.isf(sprob)
        z_b = norm.isf(self.alpha * sprob)
        possible_sample_sizes = []

        for sub_audit in self.sub_audits.values():
            p = sub_audit.sub_contest.winner_prop
            possible_sample_sizes.append(math.ceil(((z_a * math.sqrt(p * (1 - p)) - .5 * z_b) / (p - .5))**2))

        return max(possible_sample_sizes)

    def next_sample_size(self, sprob=.9, verbose=False, *args, **kwargs):
        """
        Attempt to find a next sample size estimate no greater than 10000.
        Failing that, try to find an estimate no greater than 20000, and so on.

        Args:
            sprob (float): Compute next sample for this stopping probability.
            verbose (bool): If true, the kmin and stopping probability of the next sample size will
                be returned in addition to the next sample size itself.

        Return:
            Return maxmimum next sample size estimate across all pairwise subaudits. If verbose,
                return information as specified above.
        """

        # If the audit has already terminated, there is no next_sample_size.
        if self.stopped:
            if verbose:
                return self.rounds[-1], 0, 1
            return self.rounds[-1]

        estimates = []
        for sub_audit in self.sub_audits.values():
            # Scale estimates by pairwise invalid proportion
            proportion = float(self.contest.contest_ballots) / float(sub_audit.sub_contest.contest_ballots)
            estimate = self._next_sample_size_pairwise(sub_audit, sprob)
            scaled_estimate = (int(estimate[0] * proportion), estimate[1], estimate[2])
            estimates.append(scaled_estimate)

        # Return the maximum scaled next round size estimate
        max_estimate = [0, 0, 0]
        for estimate in estimates:
            if estimate[0] > max_estimate[0]:
                max_estimate = estimate

        if verbose:
            return max_estimate
        return max_estimate[0]

    def _next_sample_size_pairwise(self, sub_audit: PairwiseAudit, sprob=0.9):
        """Compute next sample size for a single pairwise subaudit.

        Args:
            sub_audit (PairwiseAudit): Compute the sample size for this sub_audit.
            sprob (float): Get the sample size for this stopping probability.

        Return:
            Estimate in the format [sample size, kmin, stopping probability].
        """
        # NOTE: Numerical issues arise when sample results disagree to an extreme extent with the reported margin.
        start = 10000
        subsequent_round = len(self.rounds) > 0
        previous_round = 0
        if subsequent_round:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots
            init_upper_bound = self.get_upper_bound(previous_round + 1, start)
        else:
            init_upper_bound = start
        upper_bound = init_upper_bound
        while upper_bound < 10**7:
            if len(self.rounds) > 0:
                # Ensure upper bound is sufficiently large.
                if upper_bound == init_upper_bound:
                    estimate = self.binary_search_estimate(previous_round + 1, upper_bound, sprob, sub_audit)
                else:
                    estimate = self.binary_search_estimate(upper_bound // 2, upper_bound, sprob, sub_audit)
            else:
                if upper_bound == init_upper_bound:
                    estimate = self.binary_search_estimate(1, upper_bound, sprob, sub_audit)
                else:
                    estimate = self.binary_search_estimate(upper_bound // 2, upper_bound, sprob, sub_audit)
            if estimate[0] > 0:
                return estimate
            upper_bound *= 2
        return 0

    def get_upper_bound(self, n, start):
        while start <= n:
            start *= 2
        return start

    def stopping_condition_pairwise(self, pair: str, verbose: bool = False) -> bool:
        """Check, without finding the kmin, whether the subaudit is complete.

        Args:
            pair (str): Dictionary key referencing pairwise subaudit to evaluate.

        Returns:
            bool: Whether or not the pairwise stopping condition has been met.
        """
        if len(self.rounds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')
        if pair not in self.sub_audits.keys():
            raise ValueError('Candidate pait must be a valid subaudit.')

        votes_for_winner = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        tail_null = sum(self.sub_audits[pair].distribution_null[votes_for_winner:])
        tail_reported = sum(self.sub_audits[pair].distribution_reported_tally[votes_for_winner:])
        self.sub_audits[pair].pvalue_schedule.append(tail_null / tail_reported)
        if verbose:
            click.echo('\n({}) p-value: {}'.format(pair, self.sub_audits[pair].pvalue_schedule[-1]))

        self.sub_audits[pair].stopped = (self.alpha * tail_reported) > tail_null
        return self.sub_audits[pair].stopped

    def next_min_winner_ballots_pairwise(self, sub_audit: PairwiseAudit) -> int:
        """Compute stopping size for a given subaudit.

        Args:
            sub_audit (PairwiseAudit): Compute next stopping size for this subaudit.

        Return:
            int: Stopping size for most recent round.
        """
        sample_size = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] + self.sample_ballots[
            sub_audit.sub_contest.reported_loser][-1]
        return self.find_kmin(sub_audit, sample_size, False)

    def compute_min_winner_ballots(self, sub_audit: PairwiseAudit, rounds: List[int], *args, **kwargs):
        """Compute the minimum number of winner ballots for a round schedule of a pairwise audit.

        Extend the audit's round schedule with the passed (partial) round schedule, and then extend
        the audit's minimum number of winner ballots schedule with the corresponding minimums to
        meet the stopping condition.

        Args:
            sub_audit (PairwiseAudit): Compute minimum winner ballots for this Pairwise subaudit.
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
                raise ValueError('Sample size cannot exceed the total number of ballots in sub contest.')
            if i >= 1 and rounds[i] <= rounds[i - 1]:
                raise ValueError('Round schedule is cumulative and so must strictly increase.')

        previous_sample = 0
        pair = sub_audit.get_pair_str()
        for round_size in rounds:
            self.rounds.append(round_size)
            # Update current distributions for pairwise subaudit
            self._current_dist_null_pairwise(sub_audit, True)
            self._current_dist_reported_pairwise(sub_audit, True)
            # Find kmin for pairwise subaudit and append kmin
            sample_size = round_size - previous_sample
            self.find_kmin(sub_audit, sample_size, True)
            # Truncate distributions for pairwise subaudit
            self._truncate_dist_null_pairwise(pair)
            self._truncate_dist_reported_pairwise(pair)
            # Update previous round size for next sample computation
            previous_sample = round_size

    def find_kmin(self, sub_audit: PairwiseAudit, sample_size: int, append: bool):
        """Search for a kmin (minimum number of winner ballots) satisfying all stopping criteria.

        Args:
            sub_audit (PairwiseAudit): Find kmin for this subaudit.
            sample_size (int): Sample size to find kmin for.
            append (bool): Optionally append the kmins to the min_winner_ballots list. This may
                not always be desirable here because, for example, appending happens automatically
                outside this method during an interactive audit.
        """
        for possible_kmin in range(sample_size // 2 + 1, len(sub_audit.distribution_null)):
            tail_null = sum(sub_audit.distribution_null[possible_kmin:])
            tail_reported = sum(sub_audit.distribution_reported_tally[possible_kmin:])

            # Minerva's stopping criterion: tail_reported / tail_null > 1 / alpha.
            if self.alpha * tail_reported > tail_null:
                if append:
                    pair = sub_audit.get_pair_str()
                    self.sub_audits[pair].min_winner_ballots.append(possible_kmin)
                return possible_kmin

        # Sentinel of None plays nice with truncation.
        if append:
            pair = sub_audit.get_pair_str()
            self.sub_audits[pair].min_winner_ballots.append(None)
        return None

    def compute_all_min_winner_ballots(self, sub_audit: PairwiseAudit, max_sample_size: int = None, *args, **kwargs):
        """Compute the minimum number of winner ballots for the complete (that is, ballot-by-ballot)
        round schedule.

        Note: Due to limited convolutional precision, results may be off somewhat after the
            stopping probability very nearly equals 1.

        Args:
            sub_audit (PairwiseAudit): Compute minimum winner ballots for this pairwise subaudit.
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
        if max_sample_size > sub_audit.sub_contest.contest_ballots:
            max_sample_size = sub_audit.sub_contest.contest_ballots
        if max_sample_size < sub_audit.min_sample_size:
            raise ValueError("Maximum sample size must be greater than or equal to minimum size.")

        pair = sub_audit.get_pair_str()
        for sample_size in range(sub_audit.min_sample_size, max_sample_size + 1):
            self.rounds.append(sample_size)
            # First kmin computed directly.
            if sample_size == sub_audit.min_sample_size:
                self._current_dist_null_pairwise(sub_audit, True)
                self._current_dist_reported_pairwise(sub_audit, True)
                current_kmin = self.find_kmin(sub_audit, sample_size, True)
            else:
                self._current_dist_null_pairwise(sub_audit, True)
                self._current_dist_reported_pairwise(sub_audit, True)
                tail_null = sum(sub_audit.distribution_null[current_kmin:])
                tail_reported = sum(sub_audit.distribution_reported_tally[current_kmin:])
                if self.alpha * tail_reported > tail_null:
                    sub_audit.min_winner_ballots.append(current_kmin)
                else:
                    current_kmin += 1
                    sub_audit.min_winner_ballots.append(current_kmin)
            self._truncate_dist_null_pairwise(pair)
            self._truncate_dist_reported_pairwise(pair)

    def compute_risk(self, votes_for_winner: int, pair: str, *args, **kwargs):
        """Return the hypothetical pvalue if votes_for_winner were obtained in the most recent
        round."""

        sub_audit = self.sub_audits[pair]
        tail_null = sum(sub_audit.distribution_null[votes_for_winner:])
        tail_reported = sum(sub_audit.distribution_reported_tally[votes_for_winner:])

        if tail_reported == 0:
            return 0

        return tail_null / tail_reported

    def get_risk_level(self):
        """Return the risk level of an interactive Minerva audit.

        Non-interactive and bulk Minerva audits are not considered here since the sampled number of
        reported winner ballots is not available.
        """

        if len(self.pvalue_schedule) < 1:
            return None
        return min(self.pvalue_schedule)
