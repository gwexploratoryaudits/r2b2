"""Bayesian Risk-Limiting Audit module."""
import math
from typing import List

import click
import numpy as np
from scipy.stats import hypergeom as hg

from r2b2.audit import Audit
from r2b2.audit import PairwiseAudit
from r2b2.contest import Contest


class BayesianRLA(Audit):
    """Baysian Risk-Limiting Audit implementation.

    A Bayesian Risk-Limit Audit implementation as defined by Vora, et. al. for auditing 2-candidate
    plurality elections. For a given sample size, the audit software calculates a minimum number of
    votes for the reported winner that must be found in the sample to stop the audit and confirm
    the reported outcome.

    Attributes:
        alpha (float): Risk limit. Alpha represents the chance, that given an incorrectly called
            election, the audit will fail to force a full recount.
        max_fraction_to_draw (int): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        rounds (List[int]): The round sizes used during the audit.
        contest (Contest): Contest to be audited.
        prior (np.ndarray): Prior distribution for worst-case election.
    """

    prior: np.ndarray

    def __init__(self, alpha: float, max_fraction_to_draw: float, contest: Contest, reported_winner: str = None):
        """Initialize a Bayesian RLA."""

        super().__init__(alpha, 0.0, max_fraction_to_draw, False, contest)
        self.compute_priors()
        for loser, sub_audit in self.sub_audits.items():
            self.sub_audits[loser].min_sample_size = self.get_min_sample_size(sub_audit)

    def get_min_sample_size(self, sub_audit: PairwiseAudit):
        left = 1
        right = sub_audit.sub_contest.contest_ballots

        while left < right:
            proposed_min = (left + right) // 2
            proposed_min_kmin = self.next_min_winner_ballots_pairwise(sub_audit, proposed_min)

            if proposed_min_kmin == -1:
                left = proposed_min + 1
            else:
                previous_kmin = self.next_min_winner_ballots_pairwise(sub_audit, proposed_min)
                if previous_kmin == -1:
                    return proposed_min
                else:
                    right = proposed_min - 1
        return left

    def __str__(self):
        title_str = 'BayesianRLA without replacement\n-------------------------------\n'
        alpha_str = 'Risk Limit: {}\n'.format(self.alpha)
        max_frac_str = 'Maximum Fraction to Draw: {}\n'.format(self.max_fraction_to_draw)
        return title_str + alpha_str + max_frac_str + str(self.contest)

    def stopping_condition_pairwise(self, pair: str, verbose: bool = False) -> bool:
        if len(self.rounds) < 1:
            raise Exception('Attempted to call stopping condition without any rounds.')
        if pair not in self.sub_audits.keys():
            raise ValueError('pair must be a valid subaudit.')

        votes_for_winner = self.sample_ballots[self.sub_audits[pair].sub_contest.reported_winner][-1]
        risk = self.compute_risk(self.sub_audits[pair], votes_for_winner, self.rounds[-1])
        self.sub_audits[pair].pvalue_schedule.append(risk)
        if verbose:
            click.echo('\np-value: {}'.format(risk))
        return risk <= self.alpha

    def next_min_winner_ballots_pairwise(self, sub_audit: PairwiseAudit, sample_size: int = 0) -> int:
        """Compute the stopping size requirement for a given subaudit and round.

        Args:
            sample_size (int): Current round size, i.e. number of ballots to be sampled in round
            sub_audit (PairwiseAudit): Pairwise subaudit to get stopping size requirement for.

        Returns:
            int: The minimum number of votes cast for the reported winner in the current round
            size in order to stop the audit during that round. If round size is invalid, -1.
        """
        rl = sub_audit.sub_contest.reported_loser
        rw = sub_audit.sub_contest.reported_winner

        left = math.floor(sample_size / 2)
        if sample_size > 0:
            right = sample_size
        elif len(self.rounds) == 1:
            right = self.sample_ballots[rl][0] + self.sample_ballots[rw][0]
        else:
            right = (self.sample_ballots[rl][-1] - self.sample_ballots[rl][-2]) + (self.sample_ballots[rw][-1] -
                                                                                   self.sample_ballots[rw][-2])

        while left <= right:
            proposed_stop = (left + right) // 2
            proposed_stop_risk = self.compute_risk(sub_audit, proposed_stop, sample_size)

            if proposed_stop_risk == self.alpha:
                return proposed_stop

            if proposed_stop_risk < self.alpha:
                previous_stop_risk = self.compute_risk(sub_audit, proposed_stop - 1, sample_size)
                if previous_stop_risk == self.alpha:
                    return proposed_stop - 1
                if previous_stop_risk > self.alpha:
                    return proposed_stop
                right = proposed_stop - 1
            else:
                left = proposed_stop + 1

        # Handle case where kmin = sample_size
        proposed_stop_risk = self.compute_risk(sub_audit, sample_size, sample_size)
        if proposed_stop_risk <= self.alpha:
            return sample_size
        # Otherwise kmin > sample_size, so we return -1
        return -1

    def compute_priors(self) -> np.ndarray:
        """Compute prior distribution of worst case election for each pairwise subaudit."""

        for loser in self.sub_audits.keys():
            half_contest_ballots = math.floor(self.sub_audits[loser].sub_contest.contest_ballots / 2)
            left = np.zeros(half_contest_ballots, dtype=float)
            mid = np.array([0.5])
            right = np.array([(0.5 / float(half_contest_ballots))
                              for i in range(self.sub_audits[loser].sub_contest.contest_ballots - half_contest_ballots)],
                             dtype=float)
            self.sub_audits[loser].prior = np.concatenate((left, mid, right))

    def compute_risk(self, sub_audit: PairwiseAudit, votes_for_winner: int = None, current_round: int = None, *args, **kwargs) -> float:
        """Compute the risk level given current round size, votes for winner in sample, and subaudit.

        The risk level is computed using the normalized product of the prior and posterior
        distributions. The prior comes from compute_prior() and the posterior is the hypergeometric
        distribution of finding votes_for_winner from a sample of size current_round taken from a
        total size of contest_ballots. The risk is defined as the lower half of the distribution,
        i.e. the portion of the distribution associated with an incorrectly reported outcome.

        Args:
            sample (int): Votes found for reported winner in current round size.
            current_round(int): Current round size.
            sub_aduit (PairwiseAudit): Subaudit to generate risk value.

        Returns:
            float: Value for risk of given sample and round size.
        """

        posterior = np.array(
            hg.pmf(votes_for_winner, sub_audit.sub_contest.contest_ballots, np.arange(sub_audit.sub_contest.contest_ballots + 1),
                   current_round))
        posterior = sub_audit.prior * posterior
        normalize = sum(posterior)
        if normalize > 0:
            posterior = posterior / normalize

        return sum(posterior[range(math.floor(sub_audit.sub_contest.contest_ballots / 2) + 1)])

    def next_sample_size(self):
        # TODO: Documentation
        # TODO: Implement
        pass

    def compute_min_winner_ballots(self, sub_audit: PairwiseAudit, rounds: List[int], progress: bool = False, *args, **kwargs):
        """Compute the minimum number of winner ballots for a list of round sizes.

        Compute a list of minimum number of winner ballots that must be found in the
        corresponding round (sample) sizes to meet the stopping condition.

        Args:
            sub_audit (PairwiseAudit): Subaudit specifying which pair of candidates to run for.
            rounds (List[int]): List of round sizes.
            progress (bool): If True, a progress bar will display.

        Returns:
            List[int]: List of minimum winner ballots to meet the stopping conditions for each
            round size in rounds.
        """

        if len(rounds) < 1:
            raise ValueError('rounds must contain at least 1 round size.')
        previous_round = 0
        for sample_size in rounds:
            if sample_size < 1:
                raise ValueError('Sample size must be at least 1.')
            if sample_size > self.contest.contest_ballots * self.max_fraction_to_draw:
                raise ValueError('Sample size cannot be larger than max fraction to draw of the contest ballots.')
            if sample_size > sub_audit.sub_contest.contest_ballots:
                raise ValueError('Sample size cannot be larger than total ballots in subcontest.')
            if sample_size <= previous_round:
                raise ValueError('Sample sizes must be in increasing order.')
            previous_round = sample_size

        self.rounds = rounds
        min_winner_ballots = []

        if progress:
            with click.progressbar(self.rounds) as bar:
                for sample_size in bar:
                    min_winner_ballots.append(self.next_min_winner_ballots_pairwise(sub_audit, sample_size))
        else:
            for sample_size in self.rounds:
                # Append kmin for valid sample sizes, -1 for invalid sample sizes
                min_winner_ballots.append(self.next_min_winner_ballots_pairwise(sub_audit, sample_size))

        return min_winner_ballots

    def compute_all_min_winner_ballots(self,
                                       sub_audit: PairwiseAudit,
                                       max_sample_size: int = None,
                                       progress: bool = False,
                                       *args,
                                       **kwargs):
        """Compute the minimum winner ballots for all possible sample sizes.

        Args:
            max_sample_size (int): Optional. Set maximum sample size to generate stopping sizes up
                to. If not provided the maximum sample size is determined by max_fraction_to_draw
                and the total contest ballots.
            progress (bool): If True, a progress bar will display.

        Returns:
            List[int]: List of minimum winner ballots to meet the stopping condition for each round
                size in the range [min_sample_size, max_sample_size].
        """

        if max_sample_size is None:
            max_sample_size = math.ceil(self.contest.contest_ballots * self.max_fraction_to_draw)
        if max_sample_size > sub_audit.sub_contest.contest_ballots:
            max_sample_size = sub_audit.sub_contest.contest_ballots
        if max_sample_size < sub_audit.min_sample_size:
            raise ValueError('Maximum sample size must be greater than or equal to minimum size.')

        current_kmin = self.next_min_winner_ballots_pairwise(sub_audit, sub_audit.min_sample_size)
        min_winner_ballots = [current_kmin]

        # For each additional ballot, the kmin can only increase by
        if progress:
            with click.progressbar(range(sub_audit.min_sample_size + 1, max_sample_size + 1)) as bar:
                for sample_size in bar:
                    if self.compute_risk(sub_audit, current_kmin, sample_size) > self.alpha:
                        current_kmin += 1

                    min_winner_ballots.append(current_kmin)
        else:
            for sample_size in range(sub_audit.min_sample_size + 1, max_sample_size + 1):
                if self.compute_risk(sub_audit, current_kmin, sample_size) > self.alpha:
                    current_kmin += 1

                min_winner_ballots.append(current_kmin)

        return min_winner_ballots

    def get_risk_level(self, *args, **kwargs):
        pass
