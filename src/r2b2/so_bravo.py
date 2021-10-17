"""BRAVO audit module."""
import math

import click
import numpy as np

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
    def __init__(self, alpha: float, max_fraction_to_draw: float, contest: Contest):
        """Initialize a BRAVO audit."""
        super().__init__(alpha, 0.0, max_fraction_to_draw, True, contest)
        self.selection_ordered = True
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
        
        # Maintain cumulative probability of stopping.
        kmins = []
        sprobs = []
        sprob = 0

        # For each new ballot drawn, compute the probability of meeting the 
        # BRAVO stopping rule following that particular ballot draw.
        for m in range(1, marginal_draw + 1):
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
            proportion = float(self.contest.contest_ballots) / float(sub_audit.sub_contest.contest_ballots) 
            estimate = self._next_sample_size_pairwise(sub_audit, sprob)
            scaled_estimate = (math.ceil(estimate[0] * proportion), estimate[1], estimate[2], estimate[3])
            estimates.append(scaled_estimate)

        # Return the maximum scaled next round size estimate
        max_estimate = [0, 0, 0]
        for estimate in estimates:
            if estimate[0] > max_estimate[0]:
                max_estimate = estimate

        if len(self.rounds) > 0:
            if max_estimate[0] <= self.rounds[-1]:
                print("Take note... next_sample_size() erroneously selected {} when previous round size was {}.".format(max_estimate[0], self.rounds[-1]))
                max_estimate[0] = self.rounds[-1] + 1

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
        desired_sprob = sprob # Readable renaming
        # Get current audit state and prospective marginal draw.
        p = sub_audit.sub_contest.winner_prop
        kprev = 0
        nprev = 0
        if len(self.rounds) > 0:
            kprev = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1]
            nprev = kprev + self.sample_ballots[sub_audit.sub_contest.reported_loser][-1]

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
        
        # Maintain cumulative probability of stopping.
        kmins = []
        sprobs = []
        sprob = 0

        # For each new ballot drawn, compute the probability of meeting the 
        # BRAVO stopping rule following that particular ballot draw.
        m = 1
        while nprev + m < 10**7:
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

            if sprob >= desired_sprob:
                return n, sprob, kmins, sprobs

            # Update distribution for next value of m.
            num_dist_winner_next = np.append([0], num_dist) * (p)
            num_dist_loser_next = np.append(num_dist * (1 - p), [0])
            num_dist = num_dist_winner_next + num_dist_loser_next

            # Increment m.
            m += 1

        # 10^7 is unreasonably large, return -1
        raise Exception('Required next round size greater than 10^7.')
        return -1

    def stopping_condition_pairwise(self, pair: str, verbose: bool = False) -> bool:
        """Check whether the subaudit is complete. 
        Check the stopping condition for each cumulative "subsample" here.

        Args:
            pair (str): Dictionary key referencing pairwise subaudit to evaluate.

        Returns:
            bool: Whether or not the pairwise stopping condition has been met.
        """
        if len(self.rounds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')
        if pair not in self.sub_audits.keys():
            raise ValueError('Candidate pair must be a valid subaudit.')
        if self.sub_audits[pair].sub_contest.reported_winner + '_so' not in self.sample_ballots.keys() or self.sub_audits[pair].sub_contest.reported_loser + '_so' not in self.sample_ballots.keys():
            raise ValueError('Samples for SO BRAVO must also contain an ordered list of ballot samples (1 for this candidate, 0 else).')

        kprev = 0
        nprev = 0
        if len(self.rounds) > 1:
            kprev = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-2]
            nprev = kprev + self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-2]

        winner_sample = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner + '_so'][-1]
        loser_sample = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser + '_so'][-1]

        p = self.sub_audits[pair].sub_contest.winner_prop
        ktot = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        ntot = ktot + self.sample_ballots[self.sub_audits[pair].sub_contest.reported_loser][-1]

        passes = False

        kcur = kprev
        ncur = nprev
        # Check the stopping condition at each individual ballot draw
        for i in range(len(winner_sample)):
            # Only consider relevant ballots (ie for winner or loser)
            if winner_sample[i] == 1 or loser_sample[i] == 1:
                # Compute the stopping condition in the log domain
                kcur += winner_sample[i]
                ncur += 1
                loghalf = math.log(.5)
                logp = math.log(p)
                logoneminusp = math.log(1 - p)
                logoneoveralpha = math.log(1 / self.alpha)
                k = kcur
                n = ncur
                logratio = k * logp + (n - k) * logoneminusp - n * loghalf
                passes = logratio >= logoneoveralpha
                if passes:
                    self.sub_audits[pair].pvalue_schedule.append(1 / math.exp(logratio))
                    break

        if not passes:
            self.sub_audits[pair].pvalue_schedule.append(1 / math.exp(logratio))

        if verbose:
            click.echo('\n({}) p-value: {}'.format(pair, self.sub_audits[pair].pvalue_schedule[-1]))

        self.sub_audits[pair].stopped = passes
        return self.sub_audits[pair].stopped

    def next_min_winner_ballots_pairwise(self, sub_audit: PairwiseAudit) -> int:
        """Compute stopping sizes for a given subaudit. 

        Args:
            sub_audit (PairwiseAudit): Compute next stopping size for this subaudit.

        Return:
            []: Stopping sizes for most recent round as an array where the
                ith item is the kmin for the first i ballots in the SO sample.
        """
        if len(self.rounds) == len(self.min_winner_ballots):
            # This function has been called when the most recent 
            # round's min_winner_ballots has already been computed.
            return self.min_winner_ballots[-1]

        marginal_draw = self.sample_ballots[sub_audit.sub_contest.reported_winner][-1] + self.sample_ballots[
            sub_audit.sub_contest.reported_loser][-1]
        kprev = 0
        nprev = 0
        if len(self.rounds) > 1:
            kprev = self.sample_ballots[sub_audit.sub_contest.reported_winner][-2]
            nprev = kprev + self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]

        # In BRAVO, kmin is an affine function of n.
        # We can compute the constants for this affine function to make
        # computing kmin easy.
        p = sub_audit.sub_contest.winner_prop

        # Useful constant.
        logpoveroneminusp = math.log(p/(1-p))

        # Affine constants.
        intercept = math.log(1 / self.alpha) / logpoveroneminusp
        slope = math.log(1 / (2 - 2*p)) / logpoveroneminusp

        # Construct a list of kmins.
        kmins = []

        # For each marginal draw in [1, marginal_draw], compute the
        # corresponding kmin.
        for m in range(1, marginal_draw + 1):
            n = nprev + m

            # Compute kmin for n.
            kmin = math.ceil(intercept + n * slope)
            kmins.append(kmin)

        return kmins

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
        # Maintain a list of in which, for each round, there is a list of 
        # kmins for each n s.t. 1<=n<=rounds[i].
        kmin_lists = [] 
        p = sub_audit.sub_contest.winner_prop
        for i in range(len(rounds)):
            kmins_i = []
            kprev = 0
            nprev = 0
            if len(self.rounds) > 1:
                kprev = self.sample_ballots[sub_audit.sub_contest.reported_winner][-2]
                nprev = kprev + self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]
            marginal_draw = rounds[i] - nprev

            # In BRAVO, kmin is an affine function of n.
            # We can compute the constants for this affine function to make
            # computing kmin easy.

            # Useful constant.
            logpoveroneminusp = math.log(p/(1-p))

            # Affine constants.
            intercept = math.log(1 / self.alpha) / logpoveroneminusp
            slope = math.log(1 / (2 - 2*p)) / logpoveroneminusp

            # Construct a list of kmins.
            kmins_i = []

            # For each marginal draw in [1, marginal_draw], compute the
            # corresponding kmin.
            for m in range(1, marginal_draw + 1):
                n = nprev + m

                # Compute kmin for n.
                kmin = math.ceil(intercept + n * slope)
                if kmin > n:
                    kmins_i.append(-1)
                else:
                    kmins_i.append(kmin)

            kmin_lists.append(kmins_i)

        # For each of these rounds, extend the round sizes and 
        # extend the min_winner_ballots member.
        for i in range(len(rounds)):
            self.rounds.append(rounds[i])
            sub_audit.min_winner_ballots.append(kmin_lists[i])

        return kmin_lists

    def compute_risk(self, votes_for_winner: int, pair: str, *args, **kwargs):
        """
        Return hypothetical risk level if votes_for_winner votes for the 
        winner were obtained in this round.
       
        Returns:
            float: Value for risk of given votes_for_winner.
        """
        p = self.sub_audits[pair].sub_contest.winner_prop

        n = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        k = votes_for_winner

        # Compute the stopping condition in the log domain
        loghalf = math.log(.5)
        logp = math.log(p)
        logoneminusp = math.log(1 - p)
        logoneoveralpha = math.log(1 / self.alpha)
        logratio = k * logp + (n - k) * logoneminusp - n * loghalf
        risk = 1 / math.exp(logratio)

        return risk

    def get_risk_level(self):
        """Return the risk level of an interactive BRAVO audit.

            Non-interactive and bulk BRAVO audits are not considered here since the sampled number of
            reported winner ballots is not available.
        """

        if len(self.pvalue_schedule) < 1:
            return None
        return min(self.pvalue_schedule)

    def compute_all_min_winner_ballots(self, sub_audit: PairwiseAudit, max_sample_size: int = None, *args, **kwargs):
        """Compute the minimum number of winner ballots for the complete 
        (that is, ballot-by-ballot) round schedule.

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

        kprev = 0
        nprev = 0
        if len(self.rounds) > 1:
            kprev = self.sample_ballots[sub_audit.sub_contest.reported_winner][-2]
            nprev = kprev + self.sample_ballots[sub_audit.sub_contest.reported_loser][-2]
        marginal_draw = max_sample_size - nprev

        # In BRAVO, kmin is an affine function of n.
        # We can compute the constants for this affine function to make
        # computing kmin easy.

        # Useful constant.
        logpoveroneminusp = math.log(p/(1-p))

        # Affine constants.
        intercept = math.log(1 / self.alpha) / logpoveroneminusp
        slope = math.log(1 / (2 - 2*p)) / logpoveroneminusp

        # Construct a list of kmins.
        kmins = []

        # For each marginal draw in [1, marginal_draw], compute the
        # corresponding kmin.
        for m in range(1, marginal_draw + 1):
            n = nprev + m

            # Compute kmin for n.
            kmin = math.ceil(intercept + n * slope)
            kmins.append(kmin)

        self.sub_audit.min_winner_ballots.append(kmins)
