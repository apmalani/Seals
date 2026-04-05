#!/usr/bin/env python3
"""
Train SDM with N_RECORDS=100_000; write only under experiments/n100k/.
Shared ETOPO / SST cache / wind NetCDF stay in data/.
Does not modify backend/models, backend/results, or default backend/data/*.csv.
"""
import os
import sys

BACKEND = os.path.dirname(os.path.abspath(__file__))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import conf

conf.set_experiment("n100k", n_records=100_000)

import run as pipeline  # noqa: E402 — after conf is configured

if __name__ == "__main__":
    pipeline.main()
