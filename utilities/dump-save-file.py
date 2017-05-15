#!/usr/bin/env python3
"""
Utility script to dump the contents of a GradeFast save file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import argparse
import json
import os
import shelve
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["json", "yaml", "tagged-yaml"], default="json",
                        help="The output format")
    parser.add_argument("save_file", metavar="save-file",
                        help="The path to a GradeFast save file")

    args = parser.parse_args()

    if not os.path.exists(args.save_file):
        print("File not found:", args.save_file)
        sys.exit(1)

    with shelve.open(args.save_file, flag="c", protocol=4) as shelf:
        d = OrderedDict()
        for key in sorted(shelf.keys()):
            d[key] = shelf[key]
        if args.format == "yaml":
            dump_yaml(d)
        elif args.format == "tagged-yaml":
            dump_tagged_yaml(d)
        else:
            dump_json(d)
        sys.stdout.write("\n")

if __name__ == "__main__":
    main()
