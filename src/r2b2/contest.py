"""Contest module for handling individual contest data."""
from enum import Enum
from typing import Dict
from typing import List


class ContestType(Enum):
    """Enum indicating what type of vote variation was used in the contest.

    TODO: Add additional vote variations from VVSG.
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
        self.contest_ballots = contest_ballots
        self.tally = tally
        self.num_winners = num_winners
        self.reported_winners = reported_winners
        self.candidates = list(tally.keys())
        self.num_candidates = len(self.candidates)
        self.contest_type = contest_type
