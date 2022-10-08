"""Minerva 2.0 audit module."""
import math

import click
import numpy as np
from scipy.stats import binom

from r2b2.audit import Audit
from r2b2.audit import PairwiseAudit
from r2b2.contest import Contest


class Minerva2(Audit):
    """Minerva 2.0 audit implementation.

    A Minerva 2.0 audit is a type of risk-limiting audit that accounts for round-by-round auditor
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
        practical minimum instead of the theoretical minimum (BRAVO's minimum).

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
        The Minerva 2.0 kmin is no greater than the BRAVO kmin, so the latter serves
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
        satisfies_risk = self.alpha * sum_num >= sum_denom

        if len(num_dist) > 1:
            sum_num_prev = sum_num + num_dist[mid - 1]
            sum_denom_prev = sum_denom + denom_dist[mid - 1]
            satisfies_risk_prev = self.alpha * (sum_num_prev) >= (sum_denom_prev)
        else:
            # Drawing fewer ballots is impossible
            satisfies_risk_prev = False

        if satisfies_risk and not satisfies_risk_prev:
            return mid
        elif satisfies_risk and satisfies_risk_prev:
            return self.sample_size_kmin(left, mid - 1, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        elif not satisfies_risk and not satisfies_risk_prev:
            return self.sample_size_kmin(mid + 1, right, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        else:
            # To accompany Exception TODO fix method of communication
            raise Exception("sample_size_sprob: k not monotonic.")

    def find_sprob(self, n, sub_audit: PairwiseAudit):
        """Helper method to find the stopping probability of a given prospective round size."""
        p0 = (sub_audit.sub_contest.contest_ballots // 2) / sub_audit.sub_contest.contest_ballots
        p1 = sub_audit.sub_contest.winner_prop

        # The number of ballots that will be drawn this round.
        # and the previous (most recent) cumulative tally of winner ballots.
        if len(self.rounds) == 0:
            k_prev = 0
            n_prev = 0
            round_draw = n
        else:
            pair = sub_audit.get_pair_str()
            k_prev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
            n_prev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1] \
                + self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-1]
            round_draw = n - n_prev

        num_dist_round_draw = np.pad(binom.pmf(range(0, round_draw + 1), round_draw, p1), (k_prev, 0), 'constant', constant_values=(0, 0))
        denom_dist_round_draw = np.pad(binom.pmf(range(0, round_draw + 1), round_draw, p0), (k_prev, 0), 'constant', constant_values=(0, 0))
        if len(self.rounds) > 0:
            num_dist = binom.pmf(k_prev, n_prev, p1) * num_dist_round_draw
            denom_dist = binom.pmf(k_prev, n_prev, p0) * denom_dist_round_draw
        else:
            num_dist = num_dist_round_draw
            denom_dist = denom_dist_round_draw

        # We find the kmin for this would-be round size.
        right = min(self.kmin_search_upper_bound(n, sub_audit), len(num_dist))
        kmin = self.sample_size_kmin(len(num_dist) // 2, right, num_dist, denom_dist, sum(num_dist[right:]), sum(denom_dist[right:]), right)

        # If there isn't a kmin, clearly we need a larger round size.
        if kmin == 0:
            return 0, 0.0

        # What are the odds that we get as many winner ballots in the round draw
        # as are needed? That is the stopping probability.
        sprob_round = sum(num_dist_round_draw[kmin:])

        return kmin, sprob_round

    def find_sprob_using_minerva(self, n, sub_audit: PairwiseAudit):
        """Helper method to find the stopping probability of a given prospective round size."""
        p0 = (sub_audit.sub_contest.contest_ballots // 2) / sub_audit.sub_contest.contest_ballots
        p1 = sub_audit.sub_contest.winner_prop

        # Find the kmin by pretending that the new marginal draw is a first round Minerva audit
        sample_size_kmin(left, right, num_dist, denom_dist, sum_num_right, sum_denom_right, orig_right)
        kmin = self.sample_size_kmin(len(num_dist) // 2, right, num_dist, denom_dist, sum(num_dist[right:]), sum(denom_dist[right:]), right)


        # The number of ballots that will be drawn this round.
        # and the previous (most recent) cumulative tally of winner ballots.
        if len(self.rounds) == 0:
            k_prev = 0
            n_prev = 0
            round_draw = n
        else:
            pair = sub_audit.get_pair_str()
            k_prev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
            n_prev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1] \
                + self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-1]
            round_draw = n - self.rounds[-1]

        num_dist_round_draw = np.pad(binom.pmf(range(0, round_draw + 1), round_draw, p1), (k_prev, 0), 'constant', constant_values=(0, 0))
        denom_dist_round_draw = np.pad(binom.pmf(range(0, round_draw + 1), round_draw, p0), (k_prev, 0), 'constant', constant_values=(0, 0))
        if len(self.rounds) > 0:
            num_dist = binom.pmf(k_prev, n_prev, p1) * num_dist_round_draw
            denom_dist = binom.pmf(k_prev, n_prev, p0) * denom_dist_round_draw
        else:
            num_dist = num_dist_round_draw
            denom_dist = denom_dist_round_draw

        # We find the kmin for this would-be round size.
        right = min(self.kmin_search_upper_bound(n, sub_audit), len(num_dist))
        kmin = self.sample_size_kmin(len(num_dist) // 2, right, num_dist, denom_dist, sum(num_dist[right:]), sum(denom_dist[right:]), right)

        # If there isn't a kmin, clearly we need a larger round size.
        if kmin == 0:
            return 0, 0.0

        # What are the odds that we get as many winner ballots in the round draw
        # as are needed? That is the stopping probability.
        sprob_round = sum(num_dist_round_draw[kmin:])

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

    def next_sample_size(self, sprob=.9, linear_search=False, verbose=False, *args, **kwargs):
        """
        Attempt to find a next sample size estimate no greater than 10^1.
        Failing that, try to find an estimate no greater than 10^2, and so on.

        Args:
            sprob (float): Compute next sample for this stopping probability.
            verbose (bool): If true, the kmin and stopping probability of the next sample size will
                be returned in addition to the next sample size itself.
            linear_search (bool): If true then the the linear search algorithm will be used, but
                otherwise the binary search will be used by default (which is quicker).

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
            if linear_search:
                estimate = self._next_sample_size_pairwise_linear_search(sub_audit, sprob)
            else:
                estimate = self._next_sample_size_pairwise(sub_audit, sprob)
            scaled_estimate = (math.ceil(estimate[0] * proportion), estimate[1], estimate[2])
            estimates.append(scaled_estimate)

        # Return the maximum scaled next round size estimate
        max_estimate = [0, 0, 0]
        for estimate in estimates:
            if estimate[0] > max_estimate[0]:
                max_estimate = estimate
        
        # In extremely rare cases, the rounding can cause the next round size estimate to be the same
        # as the current number of ballots drawn
        if len(self.rounds) > 1:
            max_estimate = (max(max_estimate[0], self.rounds[-1] + 1), max_estimate[1], max_estimate[2])

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

        # Firstly, if this sub_audit already stopped then the next sample size for 
        # this can be 0 greater and have probability of stopping 1 and kmin same as sample size
        if sub_audit.stopped:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots
            return previous_round, 1, previous_round
        start = 10**1
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
        # Before binary search, check if one additional ballot is sufficient
        sprob_kmin_pair = self.find_sprob(previous_round + 1, sub_audit)
        if (sprob_kmin_pair[1] >= sprob):
            assert sprob_kmin_pair[0] > 0
            print('previous_round+1')
            return previous_round + 1, sprob_kmin_pair[0], sprob_kmin_pair[1]
        while upper_bound < 10**7:
            if len(self.rounds) > 0:
                # Ensure upper bound is sufficiently large.
                if upper_bound == init_upper_bound:
                    estimate = self.binary_search_estimate(previous_round + 1, upper_bound, sprob, sub_audit)
                else:
                    estimate = self.binary_search_estimate(upper_bound // 10, upper_bound, sprob, sub_audit)
            else:
                if upper_bound == init_upper_bound:
                    estimate = self.binary_search_estimate(1, upper_bound, sprob, sub_audit)
                else:
                    estimate = self.binary_search_estimate(upper_bound // 10, upper_bound, sprob, sub_audit)
            if estimate[0] > 0:
                return estimate
            upper_bound *= 10
        return -1

    def _next_sample_size_pairwise_linear_search(self, sub_audit: PairwiseAudit, sprob=0.9):
        """Compute next sample size for a single pairwise subaudit using a linear search.
            This function is never used by default and is much slower than the default binary
            search alternative found in _next_sample_size_pairwise. The linear search is more
            consistent in its results however since the lowest possible round size to achieve 
            sprob probability of stopping returned every time.

        Args:
            sub_audit (PairwiseAudit): Compute the sample size for this sub_audit.
            sprob (float): Get the sample size for this stopping probability.

        Return:
            Estimate in the format [sample size, kmin, stopping probability].
        """
        # NOTE: Numerical issues arise when sample results disagree to an extreme extent with the reported margin.
        desired_sprob = sprob # Readable renaming

        # Firstly, if this sub_audit already stopped then the next sample size for 
        # this can be 0 greater and have probability of stopping 1 and kmin same as sample size
        if sub_audit.stopped:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots
            return previous_round, 1, previous_round

        is_subsequent_round = len(self.rounds) > 0
        previous_round = 0
        if is_subsequent_round:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots

        # For each new ballot drawn, compute the probability of meeting the minerva2 stopping condition.
        n = previous_round + 1
        while n < 10**7:
            sprob_kmin_pair = self.find_sprob(n, sub_audit)
            kmin = sprob_kmin_pair[0]
            sprob = sprob_kmin_pair[1]

            # Check if we achieve the desired stopping probabilty for this round size.
            if sprob_kmin_pair[1] >= desired_sprob:
                return n, kmin, sprob

            # Increment n.
            n += 1

        # 10^7 is unreasonably large, return -1
        raise Exception('Required next round size greater than 10^7.')
        return -1

    def get_upper_bound(self, n, start):
        while start <= n:
            start *= 10
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
            raise ValueError('Candidate pair must be a valid subaudit.')

        votes_for_winner = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        tail_null = sum(self.sub_audits[pair].distribution_null[votes_for_winner:])
        tail_reported = sum(self.sub_audits[pair].distribution_reported_tally[votes_for_winner:])
        self.sub_audits[pair].pvalue_schedule.append(tail_null / tail_reported)
        if verbose:
            click.echo('\n({}) p-value: {}'.format(pair, self.sub_audits[pair].pvalue_schedule[-1]))

        self.sub_audits[pair].stopped = self.alpha * tail_reported > tail_null
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

    def compute_min_winner_ballots(self, sub_audit: PairwiseAudit, round_size: int, *args, **kwargs):
        """Compute the minimum number of winner ballots for a round schedule of a pairwise audit.

        Extend the audit's round schedule with the passed next round size, and then extend
        the audit's minimum number of winner ballots schedule with the corresponding minimum to
        meet the stopping condition.

        Args:
            sub_audit (PairwiseAudit): Compute minimum winner ballots for this Pairwise subaudit.
            rounds (int): A next round size for the audit.
        """
        if len(self.rounds) > 0 and round_size <= self.rounds[-1]:
            raise ValueError('Sample size must exceed past sample sizes.')
        if round_size < sub_audit.min_sample_size:
            raise ValueError('Sample size must be >= minimum sample size.')
        if round_size > self.contest.contest_ballots * self.max_fraction_to_draw:
            raise ValueError('Sample size cannot exceed the maximum fraction of contest ballots to draw.')
        if round_size > sub_audit.sub_contest.contest_ballots:
            raise ValueError('Sample size cannot exceed the total number of ballots in sub contest.')

        previous_sample = 0
        if len(self.rounds) > 0:
            previous_sample = self.rounds[-1]
        self.rounds.append(round_size)
        # Update current distributions for pairwise subaudit
        self._current_dist_null_pairwise(sub_audit, True)
        self._current_dist_reported_pairwise(sub_audit, True)
        # Find kmin for pairwise subaudit and append kmin
        sample_size = round_size - previous_sample
        self.find_kmin(sub_audit, sample_size, True)

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

            # Minerva 2.0 stopping condition: tail_reported / tail_null > 1 / alpha.
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

    def compute_risk(self, votes_for_winner: int, pair: str, *args, **kwargs):
        """Return the hypothetical pvalue if votes_for_winner were obtained in the most recent
        round."""

        if len(self.rounds) == 1:
            # Get relevant information
            p_0 = .5
            p_1 = self.sub_audits[pair].sub_contest.winner_prop
            n_cur = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
            k_cur = votes_for_winner

            # Compute all parts of the stopping condition
            sigma_num = 1
            sigma_denom = 1
            tau_num = sum(binom.pmf(range(), k_cur, p_1)[k_cur:])
            tau_denom = sum(binom.pmf(range(), k_cur, p_0)[k_cur:])
            tau_num = sum(binom.pmf(range(k_cur, n_cur + 1), k_cur, p_1))
            tau_denom = sum(binom.pmf(range(k_cur, n_cur + 1), k_cur, p_0))

        else:
            # Get relevant information
            p_0 = .5
            p_1 = self.sub_audits[pair].sub_contest.winner_prop
            n_cur = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1] \
                + self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-1]
            n_prev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-2] \
                + self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-2]
            k_cur = votes_for_winner
            k_prev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-2]

            # Compute all parts of the stopping condition
            sigma_num = binom.pmf(k_prev, n_prev, p_1)
            sigma_denom = binom.pmf(k_prev, n_prev, p_0)
            tau_num = sum(binom.pmf(range(k_cur - k_prev, n_cur - n_prev + 1), n_cur - n_prev, p_1))
            # TODO check
            tau_denom = sum(binom.pmf(range(k_cur - k_prev, n_cur - n_prev + 1), n_cur - n_prev, p_0))

        if tau_num == 0 or sigma_num == 0:
            return 0

        # Compute the reciprocal of omega
        pval = sigma_denom / sigma_num * tau_denom / tau_num

        return pval

    def get_risk_level(self):
        """Return the risk level of an interactive Minerva audit.

            Non-interactive and bulk Minerva audits are not considered here since the sampled number of
            reported winner ballots is not available.
        """

        if len(self.pvalue_schedule) < 1:
            return None
        return min(self.pvalue_schedule)

    def current_dist_null(self):
        """Update distribution_null for each sub audit for current round."""
        if len(self.rounds) == 0:
            raise Exception('No rounds exist.')

        # For each pairwise sub audit, update null distribution
        for sub_audit in self.sub_audits.values():
            # Update pairwise distribution using pairwise sample total as round size
            self._current_dist_null_pairwise(sub_audit)

    def _current_dist_null_pairwise(self, sub_audit: PairwiseAudit, bulk_use_round_size=False):
        """Update distribution_null for a single PairwiseAudit

        Args:
            sub_audit (PairwiseAudit): Pairwise subaudit for which to update distribution.
            bulk_use_round_size (bool): Optional argument used by bulk methods. Since the bulk
                methods do not sample ballots for candidates during the rounds, this flag simply
                uses the round schedule as the round draw (instead of the pairwise round draw)
                for updating the distribution. Default is False.
        """
        pair = sub_audit.get_pair_str()
        # If not first round get marginal sample
        if bulk_use_round_size:
            if len(self.rounds) == 1:
                round_draw = self.rounds[0]
            else:
                round_draw = self.rounds[-1] - self.rounds[-2]
        elif len(self.rounds) == 1:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

            round_draw = self.sample_ballots[sub_audit.sub_contest.reported_loser][0] + self.sample_ballots[
                sub_audit.sub_contest.reported_winner][0]
        else:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))
            round_draw = (self.sample_ballots[sub_audit.sub_contest.reported_loser][-1] -
                          self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]) + (
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] -
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-2])

        k_prev = 0
        n_prev = 0
        if len(self.rounds) > 1:
            idx = -2
            if len(self.rounds) > len(self.sample_ballots[sub_audit.sub_contest.reported_winner]):
                # In this case a new round size has been recorded, but
                # not yet the corresponding sample, so the most recent
                # sample is the previous round sample (index -1 not -2)
                idx = -1
            k_prev = self.sample_ballots[sub_audit.sub_contest.reported_winner][idx]
            n_prev = self.sample_ballots[sub_audit.sub_contest.reported_winner][idx] \
                + self.sample_ballots[sub_audit.sub_contest.reported_loser][idx]

        distribution_round_draw \
            = np.pad(binom.pmf(range(0, round_draw + 1), round_draw, .5), (k_prev, 0), 'constant', constant_values=(0, 0))

        if len(self.rounds) == 1:
            self.sub_audits[pair].distribution_null = distribution_round_draw
        else:
            self.sub_audits[pair].distribution_null \
                = binom.pmf(k_prev, n_prev, .5) * distribution_round_draw

    def current_dist_reported(self):
        """Update distribution_reported_tally for each subaudit for current round."""

        if len(self.rounds) == 0:
            raise Exception('No rounds exist')

        # For each pairwise sub audit, update dist_reported
        for sub_audit in self.sub_audits.values():
            # Update distr_reported using pairwise round size
            self._current_dist_reported_pairwise(sub_audit)

    def _current_dist_reported_pairwise(self, sub_audit: PairwiseAudit, bulk_use_round_size=False):
        """Update dist_reported for a single PairwiseAudit.

        Args:
            sub_audit (PairwiseAudit): Pairwise subaudit for which to update distribution.
            bulk_use_round_size (bool): Optional argument used by bulk methods. Since the bulk
                methods do not sample ballots for candidates during the rounds, this flag simply
                uses the round schedule as the round draw (instead of the pairwise round draw)
                for updating the distribution. Default is False.
        """

        pair = sub_audit.get_pair_str()
        # If not first round get marginal sample
        if bulk_use_round_size:
            if len(self.rounds) == 1:
                round_draw = self.rounds[0]
            else:
                round_draw = self.rounds[-1] - self.rounds[-2]
        elif len(self.rounds) == 1:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

            round_draw = self.sample_ballots[sub_audit.sub_contest.reported_loser][0] + self.sample_ballots[
                sub_audit.sub_contest.reported_winner][0]
        else:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

            round_draw = (self.sample_ballots[sub_audit.sub_contest.reported_loser][-1] -
                          self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]) + (
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] -
                              self.sample_ballots[sub_audit.sub_contest.reported_winner][-2])

        k_prev = 0
        n_prev = 0
        if len(self.rounds) > 1:
            idx = -2
            if len(self.rounds) > len(self.sample_ballots[sub_audit.sub_contest.reported_winner]):
                # In this case a new round size has been recorded, but
                # not yet the corresponding sample, so the most recent
                # sample is the last reported sample (index -1 not -2)
                idx = -1
            k_prev = self.sample_ballots[sub_audit.sub_contest.reported_winner][idx]
            n_prev = self.sample_ballots[sub_audit.sub_contest.reported_winner][idx] \
                + self.sample_ballots[sub_audit.sub_contest.reported_loser][idx]
            # NOTE same note as in null dist version of this function

        p = sub_audit.sub_contest.winner_prop
        distribution_round_draw \
            = np.pad(binom.pmf(range(0, round_draw + 1), round_draw, p), (k_prev, 0), 'constant', constant_values=(0, 0))
        if len(self.rounds) == 1:
            self.sub_audits[pair].distribution_reported_tally = distribution_round_draw
        else:
            self.sub_audits[pair].distribution_reported_tally \
                    = binom.pmf(k_prev, n_prev, p) * distribution_round_draw

    def compute_all_min_winner_ballots(self, sub_audit: PairwiseAudit, max_sample_size: int = None, *args, **kwargs):
        """
        In Minerva 2.0, the value of kmin for a round j > 1 is dependent
        on the preceding round's realized value of k. Thus we cannot
        forecast kmin values like this function is intended to do.
        """
        raise Exception('In Minerva 2.0, a kmin cannot be forecasted for future rounds until their preceding round is complete')

    def min_round_size_to_avoid_misleading_results(self, prob_not_misleading):
        """
        Assuming the announced outcome is correct, a round is called misleading if the tally has more
        ballots for the true loser than the true winner. Selecting sufficiently many ballots to avoid
        such a misleading round may be desirable given that election officials are being threatened and
        elections being generally mistrusted; drawing sufficiently many ballots that it is very likely
        that the tally will agree with announced and correct results is desirable.

        Args:
            prob_not_misleading (float in (0,1]) : the desired probability that the sample will not be misleading


        Returns:
            n, a nonnegative integer, the smallest round size for which a misleading sample will occur only 
                with probability 1 - prob_not_misleading
        """
        # If the audit has already terminated, return the most recent sample size (draw no more ballots)
        if self.stopped:
            return self.rounds[-1]

        estimates = []
        for sub_audit in self.sub_audits.values():
            # Scale estimates by pairwise invalid proportion
            proportion = float(self.contest.contest_ballots) / float(sub_audit.sub_contest.contest_ballots)
            if linear_search:
                estimate = self._sub_contest_min_round_size_to_avoid_misleading_results(sub_audit, prob_not_misleading)
            else:
                estimate = self._sub_contest_min_round_size_to_avoid_misleading_results(sub_audit, prob_not_misleading)
            scaled_estimate = math.ceil(estimate * proportion)
            estimates.append(scaled_estimate)

        # Return the maximum scaled next round size estimate
        max_estimate = 0
        for estimate in estimates:
            if estimate > max_estimate:
                max_estimate = estimate
        
        return max_estimate

    def _sub_contest_min_round_size_to_avoid_misleading_results(self, sub_audit, desired_prob_not_misleading):
        """
        Find the minumum round size to avoid misleading results just for this sub contest.

        Assuming the announced outcome is correct, a round is called misleading if the tally has more
        ballots for the true loser than the true winner. Selecting sufficiently many ballots to avoid
        such a misleading round may be desirable given that election officials are being threatened and
        elections being generally mistrusted; drawing sufficiently many ballots that it is very likely
        that the tally will agree with announced and correct results is desirable.

        Args:
            prob_not_misleading (float in (0,1]) : the desired probability that the sample will not be misleading


        Returns:
            n, a nonnegative integer, the smallest round size for which a misleading sample will occur only 
                with probability 1 - prob_not_misleading
        """
        # Firstly, if this sub_audit already stopped then return just the previous sample size for it
        if sub_audit.stopped:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots
            return previous_round

        is_subsequent_round = len(self.rounds) > 0
        previous_round = 0
        if is_subsequent_round:
            winner_ballots = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            previous_round = winner_ballots + loser_ballots

        # For each new ballot drawn, compute the probability of a misleading 
        # result (tail of binomial assuming alternative)
        n = previous_round + 1
        while n < 10**7:
            marginal_sample_size = n - previous_round
            prob_not_misleading = binom.sf(math.floor(.5*marginal_sample_size),marginal_sample_size,sub_audit.sub_contest.winner_prop)

            # Check if this round size n achieves the desired probability of not having a misleading result
            if prob_not_misleading >= desired_prob_not_misleading:
                return n

            # Increment n
            n += 1

        # 10^7 is unreasonably large, return -1
        raise Exception('Required next round size greater than 10^7.')
        return -1



