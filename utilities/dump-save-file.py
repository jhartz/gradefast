#!/usr/bin/env python3
"""
Utility script to dump the contents of a GradeFast save file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import argparse
import json
import os
import pickle
import shelve
import sqlite3
import sys
from collections import OrderedDict

# Make sure we can access the GradeFast classes, for unpickling
sys.path.insert(1, os.path.join(os.path.dirname(__file__), ".."))


class DumpJSONEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder that encodes classes based on their __dict__ or __slots__ property, or
    falls back to repr() if needed.
    """
    def default(self, o):
        if hasattr(o, "__slots__"):
            return {prop: getattr(o, prop) for prop in o.__slots__}
        if hasattr(o, "__dict__"):
            return o.__dict__
        return repr(o)


def dump_json(o):
    for chunk in DumpJSONEncoder(indent=2).iterencode(o):
        sys.stdout.write(chunk)


def dump_yaml(o):
    import yaml
    # FIXME: "encode to json --> decode from json --> encode to yaml" is hacky A.F.
    yaml.dump(json.loads(DumpJSONEncoder().encode(o)), stream=sys.stdout)


def dump_tagged_yaml(o):
    import yaml
    yaml.dump(o, stream=sys.stdout)


def get_sqlite_data(filename):
    conn = sqlite3.connect(filename)
    try:
        d = OrderedDict()

        c = conn.cursor()
        c.execute("SELECT namespace, data_key, data_value FROM gradefast "
                  "ORDER BY namespace, data_key")
        for row in c:
            namespace = str(row[0])
            key = str(row[1])
            value = pickle.loads(row[2])
            if namespace not in d:
                d[namespace] = OrderedDict()
            d[namespace][key] = value

        return d
    finally:
        conn.close()


def get_shelve_data(filename):
    with shelve.open(filename, flag="c", protocol=4) as shelf:
        d = OrderedDict()
        for key in sorted(shelf.keys()):
            d[key] = shelf[key]
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", choices=["json", "yaml", "tagged-yaml"], default="json",
                        help="The output format")
    parser.add_argument("--format", choices=["sqlite", "legacy"],
                        help="The GradeFast save file format")
    parser.add_argument("save_file", metavar="save-file",
                        help="The path to a GradeFast save file")
    args = parser.parse_args()

    if args.format == "sqlite":
        d = get_sqlite_data(args.save_file)
    elif args.format == "legacy":
        d = get_shelve_data(args.save_file)
    else:
        print("Please specify a format")
        return

    if args.output == "yaml":
        dump_yaml(d)
    elif args.output == "tagged-yaml":
        dump_tagged_yaml(d)
    else:
        dump_json(d)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
