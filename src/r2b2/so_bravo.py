"""BRAVO audit module."""
import math

import click
import numpy as np
from scipy.stats import binom

from r2b2.audit import Audit
from r2b2.audit import PairwiseAudit
from r2b2.contest import Contest


class SO_BRAVO(Audit):
    """Selection Ordered BRAVO Audit implementation.

    The BRAVO Audit (Ballot-polling Risk-limiting Audit to Verify Outcomes)
    as defined by Lindeman, Stark, and Yates, is used for auditing 2-candidate
    plurality elections. With audit samples drawn in rounds of size greater
    than one ballot (R2 audits), the BRAVO stopping rule can be applied
    once at the end of the round (EOR BRAVO), or, if the order of ballots in 
    the sample is maintained, the BRAVO stopping rule can be applied to every
    single ballot in the sample. The latter, application of the stopping rule
    to each ballot in the sample, is called Selection Ordered BRAVO (SO BRAVO).
    
    Attributes:
        alpha (float): Risk limit. Alpha represents the chance, that given an incorrectly called
            election, the audit will fail to force a full recount.
        max_fraction_to_draw (int): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        rounds (List[int]): The round sizes used during the audit.
        contest (Contest): Contest to be audited.
    """
    #TODO implement SO BRAVO
    def __init__(self, alpha: float, max_fraction_to_draw: float, contest: Contest):
        """Initialize a BRAVO audit."""
        super().__init__(alpha, 0.0, max_fraction_to_draw, True, contest)
        for pair, sub_audit in self.sub_audits.items():
            self.sub_audits[pair].min_sample_size = self.get_min_sample_size(sub_audit)

    def get_min_sample_size(self, sub_audit: PairwiseAudit, min_sprob: float = 10**(-6)):
        """Computes the theoretical minimum sample size which achieves a min_sprob 
        probability of stopping.

        Args:
            sub_audit (PairwiseAudit): Get minimum sample size for this subaudit.
            min_sprob (float): Round sizes with below min_sprob stopping probability are excluded.

        Returns:
            int: The minimum sample size of the audit, adherent to the min_sprob.
        """

        return self._next_sample_size_pairwise(sub_audit, sprob=min_sprob)[0]

    def find_sprob(self, n, sub_audit: PairwiseAudit):
        """Helper method to find the stopping probability of a given prospective round size."""
        # Get current audit state and prospective marginal draw.
        p = sub_audit.sub_contest.winner_prop
        kprev = 0
        nprev = 0
        marginal_draw = n
        if len(self.rounds) > 0:
            kprev = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            loser_ballots = self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]
            nprev = kprev + loser_ballots
            marginal_draw = n - nprev

        # In BRAVO, kmin is an affine function of n.
        # We can compute the constants for this affine function to make
        # computing kmin easy.

        # Useful constant.
        logpoveroneminusp = math.log(p/(1-p))

        # Affine constants.
        intercept = math.log(1 / self.alpha) / logpoveroneminusp
        slope = math.log(1 / (2 - 2*p)) / logpoveroneminusp

        # Distribution over drawn winner ballots for m = 1. 
        num_dist = np.array([1 - p, p])
        
        """
        # NOTE Alternatively, we could maintain a distribution over the whole
        # cumulative k. This would avoid testing against draw_min (instead of
        # directly against k_min), but would use unneeded space.
        """

        # Maintain cumulative probability of stopping.
        kmins = []
        sprobs = []
        sprob = 0

        # For each new ballot drawn, compute the probability of meeting the 
        # BRAVO stopping rule following that particular ballot draw.
        for m in range(1, marginal_draw + 1):
            assert len(num_dist) == m + 1
            n = nprev + m

            # Compute kmin for n.
            kmin = math.ceil(intercept + n * slope)

            # The corresponding stopping probability for this round size is 
            # probability that the drawn k is at least kmin.
            draw_min = kmin - kprev
            if draw_min >= len(num_dist):
                sprob_m = 0
            else:
                sprob_m = sum(num_dist[draw_min:])
                num_dist = np.append(num_dist[0 : draw_min], np.zeros(m + 1 - draw_min))

            # Record kmin, sprob_m, and updated cumulative sprob.
            kmins.append(kmin)
            sprobs.append(sprob_m)
            sprob += sprob_m

            # Update distribution for next value of m.
            num_dist_winner_next = np.append([0], num_dist) * (p)
            num_dist_loser_next = np.append(num_dist * (1 - p), [0])
            num_dist = num_dist_winner_next + num_dist_loser_next
 
        return kmins, sprob, sprobs

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
            proportion = float(sub_audit.sub_contest.contest_ballots) / float(self.contest.contest_ballots)
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

        winner_votes = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        loser_votes = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-1]
        n_cur = winner_votes + loser_votes
        p1 = self.sub_audits[pair].sub_contest.winner_prop

        null = binom.pmf(winner_votes, n_cur, .5) 
        reported = binom.pmf(winner_votes, n_cur, p1)

        self.sub_audits[pair].pvalue_schedule.append(null / reported)

        if verbose:
            click.echo('\n({}) p-value: {}'.format(pair, self.sub_audits[pair].pvalue_schedule[-1]))

        self.sub_audits[pair].stopped = self.alpha * reported >= null
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

    def compute_min_winner_ballots(self, sub_audit: PairwiseAudit, rounds: int, *args, **kwargs):
        """Compute the minimum number of winner ballots for a round schedule of a pairwise audit.

        Extend the audit's round schedule with the passed next round size, and then extend
        the audit's minimum number of winner ballots schedule with the corresponding minimum to
        meet the stopping condition.

        Args:
            sub_audit (PairwiseAudit): Compute minimum winner ballots for this Pairwise subaudit.
            rounds (List[int]): A (partial) round schedule of the audit.
        """
        for i in range(len(rounds)):
            if len(self.rounds) > 0 and rounds[i] <= self.rounds[-1]:
                raise ValueError('Sample size must exceed past sample sizes.')
            if rounds[i] < sub_audit.min_sample_size:
                raise ValueError('Sample size must be >= minimum sample size.')
            if rounds[i] > self.contest.contest_ballots * self.max_fraction_to_draw:
                raise ValueError('Sample size cannot exceed the maximum fraction of contest ballots to draw.')
            if rounds[i] > sub_audit.sub_contest.contest_ballots:
                raise ValueError('Sample size cannot exceed the total number of ballots in sub contest.')
            if i>=1 and rounds[i] <= rounds[i-1]:
                raise ValueError('Round schedule is cumulative and so must strictly increase.')

        previous_sample = 0
        pair = sub_audit.get_pair_str()
        for round_size in rounds:
            # Find kmin for pairwise subaudit and append kmin
            sample_size = round_size - previous_sample
            self.find_kmin(sub_audit, sample_size, True)
            self.rounds.append(round_size)
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
        p = sub_audit.sub_contest.winner_prop
        n = sample_size
        if len(self.rounds) >= 1:
            n = self.rounds[-1] + sample_size

        # In BRAVO, kmin is an affine function of n.
        # We can compute the constants for this affine function to make
        # computing kmin easy.

        # Useful constant.
        logpoveroneminusp = math.log(p/(1-p))

        # Affine constants.
        intercept = math.log(1 / self.alpha) / logpoveroneminusp
        slope = math.log(1 / (2 - 2*p)) / logpoveroneminusp

        # Compute kmin.
        kmin = math.ceil(intercept + n * slope)

        if append:
            pair = sub_audit.get_pair_str()
            self.sub_audits[pair].min_winner_ballots.append(kmin)

        return kmin

    def compute_risk(self, votes_for_winner: int, pair: str, *args, **kwargs):
        """
        Return hypothetical risk level if votes_for_winner votes for the 
        winner were obtained in this round.
       
        Returns:
            float: Value for risk of given votes_for_winner.
        """
        p_0 = .5
        p_1 = self.sub_audits[pair].sub_contest.winner_prop

        n_cur = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]

        null = binom.pmf(votes_for_winner, n_cur, p_0) 
        alt = binom.pmf(votes_for_winner, n_cur, p_1)

        risk = null / alt

        return risk

    def get_risk_level(self):
        """Return the risk level of an interactive BRAVO audit.

            Non-interactive and bulk BRAVO audits are not considered here since the sampled number of
            reported winner ballots is not available.
        """

        if len(self.pvalue_schedule) < 1:
            return None
        return min(self.pvalue_schedule)

    def current_dist_null(self):
        return #NOTE none needed
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
        else:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

        n = sum(self.sample_ballots[sub_audit.sub_contest.reported_loser]) + sum(self.sample_ballots[
            sub_audit.sub_contest.reported_winner])
 
        self.sub_audits[pair].distribution_null = binom.pmf(range(0,n+1), n, .5)

    def current_dist_reported(self):
        return #NOTE none needed
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
        else:
            if len(self.sample_ballots[sub_audit.sub_contest.reported_loser]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_loser]), sub_audit.sub_contest.reported_loser))
            if len(self.sample_ballots[sub_audit.sub_contest.reported_winner]) != len(self.rounds):
                raise Exception('Currently {} rounds, but only {} samples for {}.'.format(
                    len(self.rounds), len(self.sample_ballots[sub_audit.sub_contest.reported_winner]), sub_audit.stopped.reported_winner))

        n = sum(self.sample_ballots[sub_audit.sub_contest.reported_loser]) + sum(self.sample_ballots[
            sub_audit.sub_contest.reported_winner])
        p = sub_audit.sub_contest.winner_prop
 
        self.sub_audits[pair].distribution_null = binom.pmf(range(0,n+1), n, p)

    def compute_all_min_winner_ballots(self, sub_audit: PairwiseAudit, max_sample_size: int = None, *args, **kwargs):
        """Compute the minimum number of winner ballots for the complete 
        (that is, ballot-by-ballot) round schedule.
        """
        #TODO

