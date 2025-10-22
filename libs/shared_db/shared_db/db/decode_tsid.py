#!/usr/bin/env python3
"""Simple script to decode a TSID string to a long integer."""

import sys

from common.utils.tsid import TSID


def main():
    """Decode TSID string to long integer."""
    if len(sys.argv) != 2:
        print("Usage: python -m shared_db.db.decode_tsid <tsid_string>")
        sys.exit(1)

    tsid_string = sys.argv[1]

    try:
        # Decode the TSID string using from_string_by_length
        tsid = TSID.from_string_by_length(tsid_string)

        # Get the long integer value
        long_value = tsid.number

        print(f"TSID: {tsid_string}")
        print(f"Long: {long_value}")

        return long_value
    except Exception as e:
        print(f"Error decoding TSID '{tsid_string}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
