from typing import List

from r2b2.contest import Contest


class Election:
    """Election information extracted from reported results.

    A class to encompass all data from an entire election. The election's key data structue is a
    list of Contest objects which hold the relevant data from each contest within the election.

    Attributes:
        name (str): Election name.
        total_ballots (int): Total ballots cast in entire election.
        contests (List[Contest]): list of contests within the election.
    """

    name: str
    total_ballots: int
    contests: List[Contest]

    # TODO: Determine how init method should work with respect to how election results as input.
    def __init__(self, name: str, total_ballots: int):
        # TODO: Implement.
        pass

    def add_contest(self):
        # TODO: Implement.
        pass
