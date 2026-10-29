#!/bin/bash
# Harbor oracle solution. Writes the reference implementation into the
# agent's working directory.
set -euo pipefail

APP_DIR="${HARBOR_APP_DIR:-/app}"
TESTS_DIR="${HARBOR_TESTS_DIR:-/tests}"
LOGS_DIR="${HARBOR_LOGS_DIR:-/logs/verifier}"
PYTHON_BIN="${HARBOR_PYTHON:-python}"

cat > "$APP_DIR/shipping.py" << '__HARBOR_EOF__'
"""Parcel pricing against the published rate card."""


def rate_table():
    """The rate card, in dollars, keyed by ``(weight_kg, distance_km)``."""
    return {
        (0.8, 120): 4.59,
        (1.0, 0): 4.50,
        (2.5, 450): 7.83,
        (5.0, 1000): 8.70,
        (12.5, 0): 12.00,
        (22.4, 150): 14.08,
        (22.4, 1500): 23.94,
    }


def quote(weight_kg, distance_km):
    """Return the shipping cost in dollars for a single parcel."""
    return rate_table()[(weight_kg, distance_km)]
__HARBOR_EOF__
