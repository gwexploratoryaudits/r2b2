"""Contest module for handling individual contest data."""
from enum import Enum
from typing import Dict
from typing import List


class ContestType(Enum):
    """Enum indicating what type of vote variation was used in the contest.

    Todo:
        Add additional vote variations from VVSG.
    """
    PLURALITY = 0
    MAJORITY = 1


class Contest:
    """Contest information from a single contest within an Election.

    Attributes:
        contest_ballots (int): Total number of ballots cast in the contest.
        candidates (List[str]): List of candidates in the contest.
        num_candidates (int): Number of candidates in the contest.
        num_winners (int): Number of winners desired from contest.
        reported_winners (List[str]): Reported winners from contest. Must be candidates from list
            of candidates, and length should match number of winners.
        contest_type (ContestType): What type of contest is this?
        tally (Dict[str, int]): Reported tally from contest as a dictionary of candidates to
            reported votes received.
    """

    contest_ballots: int
    candidates: List[str]
    num_candidates: int
    num_winners: int
    reported_winners: List[str]
    contest_type: ContestType
    tally: Dict[str, int]

    def __init__(self, contest_ballots: int, tally: Dict[str, int],
                 num_winners: int, reported_winners: List[str],
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
                    raise TypeError(
                        'tally must contain str keys and int values')
        if sum(tally.values()) > contest_ballots:
            raise ValueError('tally contains more than contest_ballots.')
        if sum(tally.values()) < 1:
            raise ValueError(
                'tally must contain a total of at least 1 ballot.')
        if type(num_winners) is not int:
            raise TypeError('num_winners must be integer.')
        if num_winners < 1 or num_winners > len(tally):
            raise ValueError(
                'num_winners must be between 1 and number of candidates.')
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
        self.tally = tally
        self.num_winners = num_winners
        self.reported_winners = reported_winners
        self.candidates = list(tally.keys())
        self.num_candidates = len(self.candidates)
        self.contest_type = contest_type
