"""Abstract module defining an Audit framework."""
from abc import ABC
from abc import abstractmethod
from typing import List

from scipy.signal import fftconvolve
from scipy.stats import binom

from r2b2.contest import Contest


class Audit(ABC):
    """Abstract Base Class to define a general Audit object type.

    The Audit class is an abstract base class which defines the general structure and properties
    of a risk-limiting audit. Individual RLAs are subclasses of the Audit class.

    Attributes:
        alpha (float): Risk limit.  Alpha represents the chance that given an incorrectly called
            election, the audit will fail to go to a full recount.
        beta (float): the worst case chance of causing an unnecessary full recount. For many RLAs,
            beta will simply be set to 0 and will not appear to be a parameter.
        max_fraction_to_draw (float): The maximum total number of ballots auditors are willing to
            draw during the course of the audit.
        replacement (bool): Indicates if the audit sampling should be done with (true) or without
            (false) replacement.
        rounds (List[int]): List of round sizes (i.e. sample sizes).
        min_winner_ballots (List[int]): List of stopping sizes (kmin values) for each round size in
            rounds.
        sample_winner_ballots (List[int]): List of ballots found for the reported winner in each
            round size.
        risk_schedule (List[float]): Schedule of risk associated with each previous round.
            Corresponds to tail of null distribution.
        stopping_prob_schedule (List[float]): Schedule of stopping probabilities associated
            with each previous round. Corresponds to tail of reported tally distribution.
        distribution_null (List[float]): Current distribution associated with a tied election.
        distribution_reported_tally (List[float]): Current distribution associated with reported
            tally.
        contest (Contest): Contest on which to run the audit.
    """

    alpha: float
    beta: float
    max_fraction_to_draw: float
    replacement: bool
    rounds: List[int]
    min_winner_ballots: List[int]
    sample_winner_ballots: List[int]
    risk_schedule: List[float]
    stopping_prob_schedule: List[float]
    distribution_null: List[float]
    distribution_reported_tally: List[float]
    contest: Contest

    def __init__(self, alpha: float, beta: float, max_fraction_to_draw: float,
                 replacement: bool, contest: Contest):
        """Create an instance of an Audit.

        Note:
            This should only be called when initializing a subclass as the Audit class is an
            abstract class.
        """

        if type(alpha) is not float:
            raise TypeError('alpha must be a float.')
        if alpha < 0 or alpha > 1.0:
            raise ValueError('alpha value must be between 0 and 1.')
        if type(beta) is not float:
            raise TypeError('beta must be a float.')
        if beta < 0 or beta > 1.0:
            raise ValueError('beta must be between 0 and 1.')
        if type(max_fraction_to_draw) is not float:
            raise TypeError(
                'max_fraction_to_draw must be a fraction (i.e. float).')
        if max_fraction_to_draw < 0 or max_fraction_to_draw > 1:
            raise ValueError('max_fraction_to_draw must be between 0 and 1')
        if type(replacement) is not bool:
            raise TypeError('replacement must be boolean.')
        if type(contest) is not Contest:
            raise TypeError('contest must be a Contest object')

        self.alpha = alpha
        self.beta = beta
        self.max_fraction_to_draw = max_fraction_to_draw
        self.replacement = replacement
        self.contest = contest
        self.rounds = []
        self.min_winner_ballots = []
        self.sample_winner_ballots = []
        self.risk_schedule = []
        self.stopping_prob_schedule = []
        self.distribution_null = [1.0]
        self.distribution_reported_tally = [1.0]

    def current_dist_null(self, kmin: int):
        """Update distribution null and risk schedule for current round."""

        if len(self.rounds) < 2:
            round_draw = self.rounds[0]
        else:
            round_draw = self.rounds[-1] - self.rounds[-2]

        if self.replacement:
            distribution_round_draw = binom.pmf(range(0, round_draw + 1),
                                                round_draw, 0.5)
            if len(self.rounds) < 2:
                self.distribution_null = distribution_round_draw
            else:
                self.distribution_null = fftconvolve(self.distribution_null,
                                                     distribution_round_draw)
        else:
            # TODO Implement updating distributions for without replacement
            pass

        self.risk_schedule.append(self.distribution_null[kmin + 1:])
        self.distribution_null = self.distribution_reported_tally[:kmin + 1]

    def current_dist_reported(self, kmin: int):
        """Update distribution_reported_tally and stopping probability schedule for round."""

        if len(self.rounds) < 2:
            round_draw = self.rounds[0]
        else:
            round_draw = self.rounds[-1] - self.rounds[-2]

        if self.replacement:
            distribution_round_draw = binom.pmf(range(0, round_draw + 1),
                                                round_draw,
                                                self.contest.winner_prop)
            if len(self.rounds) < 2:
                self.distribution_reported_tally = distribution_round_draw
            else:
                self.distribution_reported_tally = fftconvolve(
                    self.distribution_reported_tally, distribution_round_draw)
        else:
            # TODO: Implement updating distributions for without replacement
            pass

        self.stopping_prob_schedule.append(
            self.distribution_reported_tally[kmin + 1:])
        self.distribution_reported_tally = self.distribution_reported_tally[:
                                                                            kmin
                                                                            +
                                                                            1]

    def run(self):
        """Begin interactive audit execution."""
        # TODO: documentation

        print('Beginning Audit...')
        sample_size = 0
        max_sample_size = self.contest.contest_ballots * self.max_fraction_to_draw
        previous_votes_for_winner = 0

        while sample_size < max_sample_size:
            self.next_sample_size()

            while True:
                sample_size = int(
                    input('Enter next sample size (as a running total): '))
                if sample_size < 1:
                    print('Invalid Input: Sample size must be greater than 1.')
                    continue
                if len(self.rounds) > 0 and sample_size <= self.rounds[-1]:
                    print(
                        'Invalid Input: Sample size must be greater than previous round.'
                    )
                    continue
                if sample_size > max_sample_size:
                    print('Invalid Input: Sample size cannot exceed ',
                          max_sample_size)
                    continue
                break

            while sample_size < 1 or sample_size > max_sample_size:
                print(
                    'Invalid sample size! Please enter a sample size between 1 and ',
                    max_sample_size)
                sample_size = int(
                    input('Enter next sample size (as a running total): '))

            self.rounds.append(sample_size)
            while True:
                votes_for_winner = int(
                    input(
                        'Enter total number of votes for reported winner found in sample: '
                    ))
                if votes_for_winner < 0:
                    print(
                        'Invalid Input: Votes for winner must be non-negative.'
                    )
                    continue
                if votes_for_winner < previous_votes_for_winner:
                    print('Invalid Input: Votes for winner cannot decrease.')
                    continue
                if votes_for_winner > sample_size:
                    print(
                        'Invalid Input: Votes for winner cannot exceed sample size.'
                    )
                    continue
                break

            if self.stopping_condition(votes_for_winner):
                print('Audit Complete: Stopping condition met.')
                return
            else:
                print('Stopping condition not met!!')
                force_stop = input(
                    'Would you like to force stop the audit [y/n]: ')
                if force_stop == 'y':
                    print('Audit Complete: User stopped.')
                    return

            kmin = self.next_min_winner_ballots(sample_size)
            self.min_winner_ballots.append(kmin)
            self.current_dist_null(kmin)
            self.current_dist_reported(kmin)
            previous_votes_for_winner = votes_for_winner
            self.sample_winner_ballots.append(votes_for_winner)

        print('Audit Complete: Reached max sample size.')

    @abstractmethod
    def next_sample_size(self, *args, **kwargs):
        """Generate estimates of possible next sample sizes.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def stopping_condition(self, votes_for_winner: int) -> bool:
        """Determine if the audits stopping condition has been met.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def next_min_winner_ballots(self, sample_size) -> int:
        """Compute next stopping size of given (actual) sample size.

        Note: To be used during live/interactive audit execution.
        """

        pass

    @abstractmethod
    def compute_min_winner_ballots(self, *args, **kwargs):
        """Compute the stopping size(s) for any number of sample sizes."""

        pass

    @abstractmethod
    def compute_risk(self, *args, **kwargs):
        """Compute the current risk level of the audit.

        Returns:
            Current risk level of the audit (as defined per audit implementation).
        """

        pass
