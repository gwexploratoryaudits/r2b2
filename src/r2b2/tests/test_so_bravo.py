import json
import math
import numpy as np

import pytest
from click.testing import CliRunner

from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.so_bravo import SO_BRAVO
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)
tol = 0.000001


def test_simple_so_bravo():
    simple_so_bravo = SO_BRAVO(.1, .1, default_contest)
    assert simple_so_bravo.alpha == .1
    assert simple_so_bravo.beta == 0.0
    assert simple_so_bravo.max_fraction_to_draw == .1
    assert len(simple_so_bravo.rounds) == 0
    assert len(simple_so_bravo.sub_audits) == 1
    assert simple_so_bravo.get_risk_level() is None
    simple_so_bravo.rounds.append(10)
    simple_so_bravo.stopped = True
    assert simple_so_bravo.next_sample_size() == 10
    assert simple_so_bravo.next_sample_size(verbose=True) == (10, 0, 1)


def test_so_bravo_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo = SO_BRAVO(.1, .1, contest)
    so_bravo.compute_min_winner_ballots(so_bravo.sub_audits['A-B'], [100, 200, 400])

    # From existing software
    onehundred_kmins = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, 14, 14, 15, 16, 16, 17, 17, 18, 18, 19, 19, 20, 20, 21, 22, 22, 23, 23, 24, 24, 25, 25, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 38, 38, 39, 39, 40, 40, 41, 41, 42, 43, 43, 44, 44, 45, 45, 46, 46, 47, 47, 48, 49, 49, 50, 50, 51, 51, 52, 52, 53, 54, 54, 55, 55, 56, 56, 57, 57, 58, 58, 59, 60, 60, 61, 61]
    twohundred_kmins = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, 14, 14, 15, 16, 16, 17, 17, 18, 18, 19, 19, 20, 20, 21, 22, 22, 23, 23, 24, 24, 25, 25, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 38, 38, 39, 39, 40, 40, 41, 41, 42, 43, 43, 44, 44, 45, 45, 46, 46, 47, 47, 48, 49, 49, 50, 50, 51, 51, 52, 52, 53, 54, 54, 55, 55, 56, 56, 57, 57, 58, 58, 59, 60, 60, 61, 61, 62, 62, 63, 63, 64, 65, 65, 66, 66, 67, 67, 68, 68, 69, 69, 70, 71, 71, 72, 72, 73, 73, 74, 74, 75, 76, 76, 77, 77, 78, 78, 79, 79, 80, 80, 81, 82, 82, 83, 83, 84, 84, 85, 85, 86, 87, 87, 88, 88, 89, 89, 90, 90, 91, 91, 92, 93, 93, 94, 94, 95, 95, 96, 96, 97, 98, 98, 99, 99, 100, 100, 101, 101, 102, 102, 103, 104, 104, 105, 105, 106, 106, 107, 107, 108, 109, 109, 110, 110, 111, 111, 112, 112, 113, 113, 114, 115, 115, 116, 116]
    fourhundred_kmins = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, 14, 14, 15, 16, 16, 17, 17, 18, 18, 19, 19, 20, 20, 21, 22, 22, 23, 23, 24, 24, 25, 25, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 38, 38, 39, 39, 40, 40, 41, 41, 42, 43, 43, 44, 44, 45, 45, 46, 46, 47, 47, 48, 49, 49, 50, 50, 51, 51, 52, 52, 53, 54, 54, 55, 55, 56, 56, 57, 57, 58, 58, 59, 60, 60, 61, 61, 62, 62, 63, 63, 64, 65, 65, 66, 66, 67, 67, 68, 68, 69, 69, 70, 71, 71, 72, 72, 73, 73, 74, 74, 75, 76, 76, 77, 77, 78, 78, 79, 79, 80, 80, 81, 82, 82, 83, 83, 84, 84, 85, 85, 86, 87, 87, 88, 88, 89, 89, 90, 90, 91, 91, 92, 93, 93, 94, 94, 95, 95, 96, 96, 97, 98, 98, 99, 99, 100, 100, 101, 101, 102, 102, 103, 104, 104, 105, 105, 106, 106, 107, 107, 108, 109, 109, 110, 110, 111, 111, 112, 112, 113, 113, 114, 115, 115, 116, 116, 117, 117, 118, 118, 119, 120, 120, 121, 121, 122, 122, 123, 123, 124, 125, 125, 126, 126, 127, 127, 128, 128, 129, 129, 130, 131, 131, 132, 132, 133, 133, 134, 134, 135, 136, 136, 137, 137, 138, 138, 139, 139, 140, 140, 141, 142, 142, 143, 143, 144, 144, 145, 145, 146, 147, 147, 148, 148, 149, 149, 150, 150, 151, 151, 152, 153, 153, 154, 154, 155, 155, 156, 156, 157, 158, 158, 159, 159, 160, 160, 161, 161, 162, 162, 163, 164, 164, 165, 165, 166, 166, 167, 167, 168, 169, 169, 170, 170, 171, 171, 172, 172, 173, 173, 174, 175, 175, 176, 176, 177, 177, 178, 178, 179, 180, 180, 181, 181, 182, 182, 183, 183, 184, 184, 185, 186, 186, 187, 187, 188, 188, 189, 189, 190, 191, 191, 192, 192, 193, 193, 194, 194, 195, 195, 196, 197, 197, 198, 198, 199, 199, 200, 200, 201, 202, 202, 203, 203, 204, 204, 205, 205, 206, 207, 207, 208, 208, 209, 209, 210, 210, 211, 211, 212, 213, 213, 214, 214, 215, 215, 216, 216, 217, 218, 218, 219, 219, 220, 220, 221, 221, 222, 222, 223, 224, 224, 225, 225, 226, 226]
    assert so_bravo.sub_audits['A-B'].min_winner_ballots == [onehundred_kmins, twohundred_kmins, fourhundred_kmins]


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo1 = SO_BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo2 = SO_BRAVO(.05, .05, contest2)

    assert abs(so_bravo1.sub_audits['A-B'].min_sample_size - 13) <= 2
    assert abs(so_bravo2.sub_audits['A-B'].min_sample_size - 879) <= 40


def test_execute_round_so_bravo():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo = SO_BRAVO(.1, .1, contest)
    A_so_1 = np.append(np.zeros(43), np.ones(57))
    B_so_1 = np.append(np.ones(43), np.zeros(57))
    A_so_2 = np.append(A_so_1, np.append(np.zeros(45), np.ones(55)))
    B_so_2 = np.append(B_so_1, np.append(np.ones(45), np.zeros(55)))
    A_so_3 = np.append(A_so_2, np.append(np.zeros(86), np.ones(114)))
    B_so_3 = np.append(B_so_2, np.append(np.ones(86), np.zeros(114)))
    assert not so_bravo.execute_round(100, 
            {'A': 57, 'B': 43, 'A_so': A_so_1, 'B_so': B_so_1})
    assert not so_bravo.stopped
    assert so_bravo.sample_ballots['A'] == [57]
    assert np.sum(so_bravo.sample_ballots['A_so'][-1]) == 57
    assert so_bravo.sample_ballots['B'] == [43]
    assert np.sum(so_bravo.sample_ballots['B_so'][-1]) == 43
    assert not so_bravo.sub_audits['A-B'].stopped
    assert so_bravo.rounds == [100]
    assert not so_bravo.execute_round(200, 
            {'A': 112, 'B': 88, 'A_so': A_so_2, 'B_so': B_so_2})
    assert not so_bravo.stopped
    assert so_bravo.sample_ballots['A'] == [57, 112]
    assert so_bravo.sample_ballots['B'] == [43, 88]
    assert np.sum(so_bravo.sample_ballots['A_so'][-1]) == 112
    assert np.sum(so_bravo.sample_ballots['B_so'][-1]) == 88
    assert not so_bravo.sub_audits['A-B'].stopped
    assert so_bravo.rounds == [100, 200]
    assert so_bravo.execute_round(400, 
            {'A': 226, 'B': 174, 'A_so': A_so_3, 'B_so': B_so_3})
    assert so_bravo.stopped
    assert so_bravo.sample_ballots['A'] == [57, 112, 226]
    assert so_bravo.sample_ballots['B'] == [43, 88, 174]
    assert np.sum(so_bravo.sample_ballots['A_so'][-1]) == 226
    assert np.sum(so_bravo.sample_ballots['B_so'][-1]) == 174
    assert so_bravo.sub_audits['A-B'].stopped
    assert so_bravo.rounds == [100, 200, 400]
    assert so_bravo.get_risk_level() < 0.1

def test_find_sprob_first_round():
    # Test data from github at:
    # gwexploratoryaudits/brla_explore/blob/master/B2Audits/Tables/BRAVO%20Table%20I.pdf
    ps = [.7, .65, .6, .58, .55]
    n_90perc = [60, 108, 244, 381, 974]
    for i in range(len(ps)):
        N = 1000
        A_tally = int(N*ps[i])
        B_tally = N - A_tally
        contest = Contest(N, {'A': A_tally, 'B': B_tally}, 1, ['A'], ContestType.MAJORITY)
        so_bravo = SO_BRAVO(.1, .1, contest)
        assert abs(so_bravo.find_sprob(n_90perc[i], so_bravo.sub_audits['A-B'])[1] - .9) <= .005

def test_next_sample_size_first_round():
    # Test data from github at:
    # gwexploratoryaudits/brla_explore/blob/master/B2Audits/Tables/BRAVO%20Table%20I.pdf
    ps = [.7, .65, .6, .58, .55]
    desired_sprob = .9
    n_90perc = [60, 108, 244, 381, 974]
    for i in range(len(ps)):
        N = 1000
        A_tally = int(N*ps[i])
        B_tally = N - A_tally
        contest = Contest(N, {'A': A_tally, 'B': B_tally}, 1, ['A'], ContestType.MAJORITY)
        so_bravo = SO_BRAVO(.1, .1, contest)
        assert abs(so_bravo.next_sample_size(sprob=desired_sprob) - n_90perc[i]) <= 0

test_simple_so_bravo()
test_so_bravo_kmins()
test_min_sample_size()
test_execute_round_so_bravo()
test_find_sprob_first_round()
test_next_sample_size_first_round()
