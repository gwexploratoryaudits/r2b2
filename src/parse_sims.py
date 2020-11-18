#!/usr/bin/env python
"""Parse output of multi_round_sim for analysis"""

import argparse
import re
import json
from collections import defaultdict
from operator import itemgetter

def parse_debug(str):
    """Parse string containing f-string Python debug output separated by commas
    """

    if 'relevant_sample_size' in str:
        j = str.replace("'", '"')
        if "inf" in j:
            j = j.replace("inf", "9999999")
        return json.loads(j)
        
    if not any(marker in str for marker in ['seed']):
        return {}

    fields = splitpat.split(str)
    if len(fields) < 2:
        return {}
    return dict(map(lambda field: field.split('=', 2), fields))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='file to parse')

    args = parser.parse_args()

    splitpat = re.compile(", (?=[a-zA-Z])")
    acc = defaultdict(list)
    with open(args.filename) as f:
        for res in [parse_debug(line) for line in f.readlines()]:
            acc[frozenset(res.keys())].append(res)

    for schema, rows in acc.items():
        print(f"{len(rows)=} rows in {schema=}")

        if 'relevant_sample_size' in schema:
            rows.sort(key=itemgetter("p_value"))
            print("Lowest 10 pvalues:", *rows[:10], sep='\n')
            print("Highest 10 pvalues:", *rows[-10:], sep='\n')
