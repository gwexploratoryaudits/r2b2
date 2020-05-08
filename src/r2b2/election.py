"""Election module handles data associated with an Election or collection of Contests."""
from typing import Dict

from r2b2.contest import Contest


class Election:
    """Election information extracted from reported results.

    A class to encompass all data from an entire election. The election's key data structue is a
    list of Contest objects which hold the relevant data from each contest within the election.

    Attributes:
        name (str): Election name.
        total_ballots (int): Total ballots cast in entire election.
        contests (Dict[str, Contest]): dict of contests within the election with names as keys.
    """

    name: str
    total_ballots: int
    contests: Dict[str, Contest]

    def __init__(self, name: str, total_ballots: int, contests: Dict[str, Contest]):
        if type(name) is not str:
            raise TypeError('name must be a string')
        if type(total_ballots) is not int:
            raise TypeError('total_ballots must be an integer value.')
        if type(contests) is not dict:
            raise TypeError('contests must be a dict of Contest objects.')
        else:
            for c in contests.values():
                if type(c) is not Contest:
                    raise TypeError('contests must be a dict of Contest objects.')
        if total_ballots < 1:
            raise ValueError('total_ballots must be greater than 0.')

        self.name = name
        self.total_ballots = total_ballots
        self.contests = contests

    def __repr__(self):
        contests_str = '['
        for contest in self.contests.values():
            contests_str += repr(contest)
            contests_str += ', '
        contests_str += ']'
        return '{}: [{}, {}, {}]'.format(self.__class__.__name__, self.name, self.total_ballots, contests_str)

    def __str__(self):
        title_str = 'Election\n--------\n'
        name_str = 'Name: {}\n'.format(self.name)
        ballot_str = 'Total Ballots: {}\n'.format(self.total_ballots)
        contests_str = 'List of Contests:\n'
        for name, contest in self.contests.items():
            contests_str += '\n' + name + '\n'
            contests_str += str(contest)
        return title_str + name_str + ballot_str + contests_str

    def add_contest(self):
        # TODO: Implement.
        pass
