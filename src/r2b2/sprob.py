"""Stopping probability module."""
from typing import List

from scipy.signal import fftconvolve
from scipy.stats import binom

from r2b2.contest import Contest


class Sprob():
    """Stopping probability functionality implementation.

    Audits can be represented as a sequence of increasing round sizes and kmins. This module takes
    those lists and computes the stopping probabilities (or risks) for the audit. There may be a
    discrepancy between an audit's self-reported stopping probabilities and the stopping probabilities
    computed here. This can be the result of an audit scheme incorporating conservative assumptions
    (e.g., a ballot-by-ballot decision) that are not applicable to the round schedule at hand.

    This module does not generate kmins from scratch, and so is not a subclass of Audit. This module
    assumes ballots are drawn with replacement.

    The stopping probabilities reported are non-cumulative.

    Attributes:
        rounds (List[int]): Cumulative round schedule.
        min_winner_ballots (List[int]): Stopping sizes (or kmins) respective to the round schedule.
        contest (Contest): Contest to be audited.
    """

    def __init__(self, rounds: List[int], min_winner_ballots: List[int], contest: Contest):
        self.rounds = rounds
        self.min_winner_ballots = min_winner_ballots
        self.contest = contest

        self.distribution = []

        self.sprobs = []

    def compute_sprobs(self):
        """Returns an array non-cumulative stopping probabilities, respective to the rounds."""

        if len(self.rounds) < 1:
            raise Exception("Round schedule must contain at least 1 round.")
        if len(self.rounds) != len(self.min_winner_ballots):
            raise Exception("Round and kmin schedules must have the same length.")
        if self.rounds[0] < 1:
            raise ValueError("Round sizes must be >= 1.")
        if self.min_winner_ballots[0] < 1:
            raise ValueError("Kmins must be >= 1.")
        if self.min_winner_ballots[0] > self.rounds[0]:
            raise ValueError("Kmins cannot exceed respective round sizes.")
        for i in range(1, len(self.rounds)):
            if self.rounds[i] <= self.rounds[i-1]:
                raise ValueError("Round schedule must strictly increase.")
            if self.min_winner_ballots[i] > self.rounds[i]:
                raise ValueError("Kmins cannot exceed respective round sizes.")

        self.sprobs = []

        for i in range(len(self.rounds)):
            self.current_dist(i)
            self.truncate_dist(i)

        return self.sprobs

    def current_dist(self, round_index):
        """Generates the current round distribution: a binomial for the first round and a convolution
        of a binomial and a quasi-binomial thereafter."""
        p = self.contest.winner_prop
        if round_index == 0:
            n = self.rounds[round_index]
            self.distribution = binom.pmf(range(0, n + 1), n, p)
        else:
            n = self.rounds[round_index] - self.rounds[round_index - 1]
            self.distribution = fftconvolve(self.distribution, binom.pmf(range(0, n + 1), n, p))

    def truncate_dist(self, round_index):
        """Sums and truncates the distribution at the kmin."""
        self.sprobs.append(sum(self.distribution[self.min_winner_ballots[round_index]:]))
        self.distribution = self.distribution[:self.min_winner_ballots[round_index]]

    def expectation(self):
        """Returns the average number of ballots audited under the given schedule of round sizes
        and kmins."""
        if len(self.sprobs) != len(self.rounds):
            self.compute_sprobs

        return (sum([self.rounds[i] * self.sprobs[i] for i in range(len(self.rounds))]) +
                (1 - sum(self.sprobs)) * self.contest.contest_ballots)
