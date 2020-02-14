from enum import Enum
from typing import List, Dict


class ContestType(Enum):
    PLURALITY = 1


class Contest:
    """Contest information from a single contest within an Election.

    Attributes
        total_ballots_cast (int): Total number of ballots cast in the contest.
        candidates (List[str]): List of candidates in the contest.
        num_candidates (int): Number of candidates in the contest.
        num_winners (int): Number of winners desired from contest.
        reported_winners (List[str]): Reported winners from contest. Must be candidates from list
            of candidates, and length should match number of winners.
        contest_type (ContestType): What type of contest is this?
        tally (Dict[str, int]): Reported tally from contest as a dictionary of candidates to
            reported votes received.
    """

    total_ballots_cast: int
    candidates: List[str]
    num_candidates: int
    num_winners: int
    reported_winners: List[str]
    contest_type: ContestType
    tally: Dict[str, int]

    def __init__(self, total_ballots_cast: int, tally: Dict[str, int],
                 num_winners: int, reported_winners: List[str],
                 contest_type: ContestType):
        self.total_ballots_cast = total_ballots_cast
        self.tally = tally
        self.num_winners = num_winners
        self.reported_winners = reported_winners
        self.candidates = list(tally.getKeys())
        self.num_candidates = len(self.candidates)
        self.contest_type = contest_type
