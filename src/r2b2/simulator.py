"""R2B2 Simulation Module."""
import json
import os
from abc import ABC
from abc import abstractmethod
from typing import List

from matplotlib import pyplot as plt
from pymongo import MongoClient

from r2b2.contest import Contest


class DBInterface():
    """Class for handling MongoDB operations."""
    def __init__(self, host='localhost', port=27017, name='r2b2', user='reader', pwd='icanread'):
        self.client = MongoClient(host=host, port=port, username=user, password=pwd)
        self.db = self.client[name]

    def audit_lookup(self, audit_type: str, alpha: float, qapp: dict = None, *args, **kwargs):
        """Find/Create an audit in database.

        Searches through database for an existing audit entry with the given parameters.
        If none exists, an audit entry is created for the parameters.

        Args:
            audit_type (str): Name of audit, for example: 'minerva', 'brla', etc.
            alpha (float): Risk-limit of audit.
            qapp (dict): Optional parameter that appends dict to mongo query.

        Returns:
            ObjectID of new or existing audit entry.
        """
        audits = self.db.audits
        query = {'audit_type': audit_type, 'alpha': alpha}
        if qapp is not None:
            query.update(qapp)
        # TODO: handle additional arguments

        audit = audits.find_one(query)
        if audit is not None:
            return audit['_id']

        return audits.insert_one(query).inserted_id

    def contest_lookup(self, contest: Contest, qapp: dict = None, *args, **kwargs):
        """Find/Create a contest in database.

        Searches through database for an existing contest entry with the given parameters.
        If none exists, a contest entry is created.

        Args:
            contest (r2b2.contest.Contest): Contest with attributes to be used in the database query.
            qapp (dict): Optional parameter that appends dict to mongo query.

        Returns:
            ObjectID of new of existing contest entry.
        """
        contests = self.db.contests
        query = {
            'contest_ballots': contest.contest_ballots,
            'tally': contest.tally,
            'num_winners': contest.num_winners,
            'reported_winners': contest.reported_winners
        }
        if qapp is not None:
            query.update(qapp)
        # TODO: handle additional things
        contest = contests.find_one(query)
        if contest is not None:
            return contest['_id']
        return contests.insert_one(query).inserted_id

    def simulation_lookup(self, audit, reported, underlying, invalid, qapp: dict = None, *args, **kwargs):
        """Find/Create a simulation in database.

        Searches through database for an existing simulation entry with the given parameters.
        If none exists, a simulation entry is created.

        Args:
            audit: ObjectID of audit entry (from audits collection) used in the simulation.
            reported: ObjectID of reported contest entry (from contests collection) used in the
                simulation.
            underlying: Description of the underlying contest used in the simulation. Could be an
                ObjectID from the contests table, could simply be a string indicating a tie,
                depends on the specific simulation.
            qapp (dict): Optional parameter that appends dict to mongo query.

        Returns:
            ObjectID of new or existing simulation entry.
        """
        simulations = self.db.simulations
        query = {'reported': reported, 'underlying': underlying, 'audit': audit, 'invalid_ballots': invalid}
        if qapp is not None:
            query.update(qapp)
        # TODO: Handle additional things
        simulation = simulations.find_one(query)
        if simulation is not None:
            return simulation['_id']
        return simulations.insert_one(query).inserted_id

    def trial_lookup(self, sim_id, *args, **kwargs):
        """Find all trials for a given simulation ObjectID"""
        return self.db.trials.find({'simulation': sim_id})

    def write_trial(self, entry):
        """Write a trial document into the trials collection."""
        self.db.trials.insert_one(entry)

    def update_analysis(self, sim_id, entry):
        """Update analysis in simulation document."""
        self.db.simulations.update_one({'_id': sim_id}, {'$set': {'analysis': entry}})


class Simulation(ABC):
    """Abstract Base Class to define a simulation.

    Attributes:
        db_mode (bool): Indicates if simulation is running in Database mode or local mode.
        audit_type (str): Indicates what type of audit is simulated.
        alpha (float): Risk-limit of simulation.
        audit_id (str): ObjectID of audit entry from audits collection in MongoDB.
        reported (Contest): Reported contest results that are audited during simulation.
        reported_id (str): ObjectID of reported contest entry from contests collection in MongoDB.
        underlying (str): Indicates the true underlying contest results ballots are drawn from
            during the simulation. This might be an ObjectID similar to reported_id, it might be
            a string simply indicating that the underlying distribution is a tie. This field is
            specified by a specific simulation implementation.
        sim_id (str): ObjectID of simulation from simulations collection in MongoDB defined by the
            reported contest, underlying contest, and audit.
        trials: List of trials performed in run() method. Trials are dicts formatted for
            JSON output or MongoDB document entry.
    """

    db_mode: bool
    db: DBInterface
    audit_type: str
    alpha: float
    audit_id: str
    reported: Contest
    reported_id: str
    underlying: str
    invalid: bool
    sim_id: str
    trials: List

    def __init__(self,
                 audit_type: str,
                 alpha: float,
                 reported: Contest,
                 underlying,
                 invalid: bool,
                 db_mode=True,
                 db_host='localhost',
                 db_port=27017,
                 db_name='r2b2',
                 user='reader',
                 pwd='icanread',
                 *args,
                 **kwargs):
        self.audit_type = audit_type
        self.alpha = alpha
        self.reported = reported
        self.underlying = underlying
        self.invalid = invalid
        self.db_mode = db_mode
        self.trials = []
        if not self.db_mode:
            self.db = None
            self.audit_id = None
            self.reported_id = None
            self.sim_id = None

        else:
            self.db = DBInterface(db_host, db_port, db_name, user, pwd)
            if 'audit_args' in kwargs:
                self.audit_id = self.db.audit_lookup(audit_type, alpha, qapp=kwargs['audit_args'])
            else:
                self.audit_id = self.db.audit_lookup(audit_type, alpha)
            if 'reported_args' in kwargs:
                self.reported_id = self.db.contest_lookup(reported, qapp=kwargs['reported_args'])
            else:
                self.reported_id = self.db.contest_lookup(reported)
            if 'sim_args' in kwargs:
                self.sim_id = self.db.simulation_lookup(self.audit_id,
                                                        self.reported_id,
                                                        self.underlying,
                                                        self.invalid,
                                                        qapp=kwargs['sim_args'])
            else:
                self.sim_id = self.db.simulation_lookup(self.audit_id, self.reported_id, self.underlying, self.invalid)

    def run(self, n: int):
        """Execute n trials of the simulation.

        Executes n simulation trials by generating a random seed, running a trial with the given
        seed, and writing the trial entry to the trials collection.

        Args:
            n (int): Number of trials to execute and write to database.
        """

        for i in range(n):
            curr_seed = self.get_seed()
            trial_entry = {'simulation': self.sim_id, 'seed': str(curr_seed)}
            trial_entry.update(self.trial(curr_seed))
            self.trials.append(trial_entry)
            if self.db_mode:
                self.db.write_trial(trial_entry)

    def get_seed(self):
        """Generate a random seed.

        Note:
            This method generates 8 random bytes using os sources of randomness. If a different
            source of randomness is desired, overwrite the method per implementation.
        """
        return os.urandom(8)

    def output(self, fd: str = None):
        """Write output of simulation to JSON file.

        Args:
            fd (str): filename to write output to. If no file is passed, formatted JSON is
                simply printed.
        """
        if self.db_mode:
            raise Exception('output() should only be called in local mode.')

        output = {}
        output['audit'] = self.output_audit()
        output['reported'] = self.reported.to_json()
        if type(self.underlying) is Contest:
            output['underlying'] = self.underlying.to_json()
        else:
            output['underlying'] = self.underlying
        output['trials'] = self.trials
        if fd is None:
            print(json.dumps(output, indent=4))
            return

        with open(fd, 'w') as outfile:
            json.dump(output, outfile, indent=4)

    def output_audit(self):
        """Create audit output in JSON format.

        Note:
            This functionality is separated into a method so specific audit implementations may
            override it and customize their output in non-database mode.
        """
        return {'audit_type': self.audit_type, 'alpha': self.alpha}

    @abstractmethod
    def trial(self, seed):
        """Execute a single trial given a random seed."""
        pass

    @abstractmethod
    def analyze(self, *args, **kwargs):
        """Analyze the simulation trials."""
        pass


def histogram(values: List, xlabel: str, bins='auto'):
    """Create a histogram for a given dataset."""
    plt.hist(values, bins=bins, rwidth=0.9)
    plt.grid(axis='y')
    plt.xlabel(xlabel)
    plt.ylabel('Frequency')
    plt.show()
