"""Contest module for handling individual contest data."""
from enum import Enum
from typing import Dict
from typing import List


class ContestType(Enum):
    """Enum indicating what type of vote variation was used in the contest."""

    # TODO: Add additional vote variations from VVSG.
    PLURALITY = 0
    MAJORITY = 1


class PairwiseContest:
    """Simple 2-candidate, no irrelevant ballot sub contests of a Contest."""

    contest_ballots: int
    reported_winner: str
    reported_loser: str
    reported_winner_ballots: int
    reported_loser_ballots: int
    winner_prop: float

    def __init__(self, reported_winner: str, reported_loser: str, reported_winner_ballots: int, reported_loser_ballots: int):
        self.contest_ballots = reported_winner_ballots + reported_loser_ballots
        self.reported_winner = reported_winner
        self.reported_loser = reported_loser
        self.reported_winner_ballots = reported_winner_ballots
        self.reported_loser_ballots = reported_loser_ballots
        self.winner_prop = float(reported_winner_ballots) / float(self.contest_ballots)


class Contest:
    """Contest information from a single contest within an Election.

    Attributes:
        contest_ballots (int): Total number of ballots cast in the contest.
        irrelevant_ballots (int): Number of ballots not attributed to a candidate in the tally.
        candidates (List[str]): List of candidates in the contest sorted (descending) by tally.
        num_candidates (int): Number of candidates in the contest.
        num_winners (int): Number of winners desired from contest.
        reported_winners (List[str]): Reported winners from contest. Must be candidates from list
            of candidates, and length should match number of winners. Stored in same order as
            sorted candidates.
        contest_type (ContestType): What type of contest is this?
        tally (Dict[str, int]): Reported tally from contest as a dictionary of candidates to
            reported votes received.
        winner_prop (float): Proportion of ballots cast for reported winner. Currently for first
            winner listed in reported winners.
        sub_contests (Dict[str, Dict[str, List[int]]]): Collection of pairwise sub-contests for
            each (reported winner, candidate) pair where the reported winner has more than 50% of
            the total sub-contest ballots, i.e. where the reported winner has a greater reported
            tally than the other candidate. These pairs provide the two-candidate, no irrelevant
            ballots assumption required by some audits.
    """

    contest_ballots: int
    irrelevant_ballots: int
    candidates: List[str]
    num_candidates: int
    num_winners: int
    reported_winners: List[str]
    contest_type: ContestType
    tally: Dict[str, int]
    winner_prop: float
    sub_contests: List[PairwiseContest]

    def __init__(self, contest_ballots: int, tally: Dict[str, int], num_winners: int, reported_winners: List[str],
                 contest_type: ContestType):

        if type(contest_ballots) is not int:
            raise TypeError('contest_ballots must be integer.')
        if contest_ballots < 1:
            raise ValueError('contest_ballots must be at least 1.')
        if type(tally) is not dict:
            raise TypeError('tally must be a dict.')
        else:
            for k, v in tally.items():
                if type(k) is not str or type(v) is not int:
                    raise TypeError('tally must contain str keys and int values')
        if sum(tally.values()) > contest_ballots:
            raise ValueError('tally total is greater than contest_ballots.')
        if sum(tally.values()) < 1:
            raise ValueError('tally must contain a total of at least 1 ballot.')
        if type(num_winners) is not int:
            raise TypeError('num_winners must be integer.')
        if num_winners < 1 or num_winners > len(tally):
            raise ValueError('num_winners must be between 1 and number of candidates.')
        if type(reported_winners) is not list:
            raise TypeError('reported_winners must be a list[str].')
        elif len(reported_winners) != num_winners:
            raise ValueError('reported_winners must be of length num_winners')
        else:
            for w in reported_winners:
                if type(w) is not str:
                    raise TypeError('reported_winners must be a list[str].')
                if w not in tally.keys():
                    raise ValueError('reported winners must be candidates.')
        if type(contest_type) is not ContestType:
            raise TypeError('contest_type must be ContestType Enum object.')

        self.contest_ballots = contest_ballots
        self.irrelevant_ballots = contest_ballots = sum(tally.values())
        self.tally = tally
        self.num_winners = num_winners
        self.reported_winners = []
        self.candidates = sorted(tally.keys(), key=tally.get, reverse=True)
        self.num_candidates = len(self.candidates)
        self.reported_winners = sorted(reported_winners, key=self.candidates.index)
        self.contest_type = contest_type
        self.winner_prop = float(self.tally[self.reported_winners[0]]) / float(self.contest_ballots)
        # For each reported winner get pairwise sub-contests where they have > 50% of the (sub)tally
        # These sub-contests provide the two-candidate, no-irrelevant ballots assumption
        self.sub_contests = []
        for rw in self.reported_winners:
            rw_ballots = self.tally[rw]
            for candidate in self.candidates:
                if rw_ballots > self.tally[candidate]:
                    self.sub_contests.append(PairwiseContest(rw, candidate, rw_ballots, self.tally[candidate]))

    def find_sub_contest(self, reported_winner, reported_loser):
        for i in range(len(self.sub_contests)):
            if self.sub_contests[i].reported_winner == reported_winner and self.sub_contests[i].reported_loser == reported_loser:
                return i
        return -1

    def __repr__(self):
        """String representation of Contest class."""
        return '{}: [{}, {}, {}, {}, {}]'.format(self.__class__.__name__, self.contest_ballots, self.tally, self.num_winners,
                                                 self.reported_winners, repr(self.contest_type))

    def __str__(self):
        """Human readable string representation of audit class."""
        title_str = 'Contest\n-------\n'
        ballot_str = 'Contest Ballots: {}\n'.format(self.contest_ballots)
        tally_str = 'Reported Tallies:\n'
        for candidate in self.candidates:
            tally_str += '     {:<15} {}\n'.format(candidate, self.tally[candidate])
        winner_str = 'Reported Winners: {}\n'.format(self.reported_winners)
        type_str = 'Contest Type: {}\n'.format(self.contest_type)
        return title_str + ballot_str + tally_str + winner_str + type_str + '\n'
