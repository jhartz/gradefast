import unittest

from gradefast.models import CommandItem, CommandSet, GradeScore, GradeSection
from gradefast.parsers import ModelParseError, _parse_list, \
    parse_commands, parse_grade_structure, parse_settings


class TestParseList(unittest.TestCase):
    @staticmethod
    def call_parse_list(lst, calls_list, path=None):
        return _parse_list(lst,
                           lambda d, p, s: calls_list.append((d, p, s)) or d,
                           path)

    def test_empty_list(self):
        calls = []
        results = self.call_parse_list([], calls)
        self.assertEqual(len(results), 0)
        self.assertEqual(len(calls), 0)

    def test_single_item_list(self):
        lst = [{}]
        calls = []
        results = self.call_parse_list(lst, calls)
        self.assertListEqual(results, lst)
        self.assertListEqual(calls, [({}, [1], "#1")])
        self.assertIs(results[0], lst[0])

    def test_multi_item_list(self):
        lst = [{}, {}, {}]
        calls = []
        results = self.call_parse_list(lst, calls)
        self.assertListEqual(results, lst)
        self.assertListEqual(calls, [
            ({}, [1], "#1"),
            ({}, [2], "#2"),
            ({}, [3], "#3"),
        ])
        self.assertIs(results[0], lst[0])
        self.assertIs(results[1], lst[1])
        self.assertIs(results[2], lst[2])

    def test_single_item_list_with_path(self):
        lst = [{}]
        calls = []
        self.call_parse_list(lst, calls, [5, 6, 7])
        self.assertListEqual(calls, [({}, [5, 6, 7, 1], "#5.6.7.1")])

    def test_multi_item_list_with_path(self):
        lst = [{}, {}, {}]
        calls = []
        results = self.call_parse_list(lst, calls, [6, 9])
        self.assertListEqual(results, lst)
        self.assertListEqual(calls, [
            ({}, [6, 9, 1], "#6.9.1"),
            ({}, [6, 9, 2], "#6.9.2"),
            ({}, [6, 9, 3], "#6.9.3"),
        ])
        self.assertIs(results[0], lst[0])
        self.assertIs(results[1], lst[1])
        self.assertIs(results[2], lst[2])


class TestParseCommands(unittest.TestCase):
    def test_simple_command_item(self):
        commands = parse_commands([
            {
                "name": "My Innocent Command",
                "command": "rm -rf /"
            }
        ])
        self.assertListEqual(commands, [
            CommandItem(
                name="My Innocent Command",
                command="rm -rf /"
            )
        ])

    def test_simple_command_set(self):
        commands = parse_commands([
            {
                "commands": []
            }
        ])
        self.assertListEqual(commands, [
            CommandSet(
                commands=[]
            )
        ])

    def test_nested_commands(self):
        commands = parse_commands([
            {
                "name": "Top-level command",
                "command": "ls -alF",
                "environment": {
                    "ABC": "def"
                },
                "background": True,
                "passthrough": False,
                "stdin": "My my my"
            },
            {
                "name": "Sub-commands",
                "folder": "abc",
                "environment": {
                    "ABC": "ghi"
                },
                "commands": [
                    {
                        "name": "Second-level command",
                        "command": "rm -rf /"
                    },
                    {
                        "commands": [
                            {
                                "name": "Third-level command",
                                "command": "sudo cat /etc/passwd"
                            }
                        ]
                    }
                ]
            }
        ])
        self.assertListEqual(commands, [
            CommandItem(
                name="Top-level command",
                command="ls -alF",
                environment={
                    "ABC": "def"
                },
                is_background=True,
                is_passthrough=False,
                stdin="My my my"
            ),
            CommandSet(
                name="Sub-commands",
                folder="abc",
                environment={
                    "ABC": "ghi"
                },
                commands=[
                    CommandItem(
                        name="Second-level command",
                        command="rm -rf /"
                    ),
                    CommandSet(
                        commands=[
                            CommandItem(
                                name="Third-level command",
                                command="sudo cat /etc/passwd"
                            )
                        ]
                    )
                ]
            )
        ])

    def test_command_and_commands(self):
        with self.assertRaises(ModelParseError) as assertion:
            parse_commands([
                {
                    "command": "",
                    "commands": []
                }
            ])

        self.assertIn("has both \"command\" and \"commands\"", str(assertion.exception))

        with self.assertRaises(ModelParseError) as assertion:
            parse_commands([{}])

        self.assertIn("has neither \"command\" nor \"commands\"", str(assertion.exception))

    def test_command_set_invalid_properties(self):
        with self.assertRaises(ModelParseError) as assertion:
            parse_commands([
                {
                    "commands": [],
                    "bad prop": True
                }
            ])

        self.assertIn("has an invalid property: \"bad prop\"", str(assertion.exception))

    def test_command_item_missing_name(self):
        with self.assertRaises(ModelParseError) as assertion:
            parse_commands([
                {
                    "command": "echo Hello World"
                }
            ])

        self.assertIn("missing \"name\"", str(assertion.exception))

    def test_command_item_invalid_properties(self):
        with self.assertRaises(ModelParseError) as assertion:
            parse_commands([
                {
                    "name": "test 2",
                    "command": "[ -z ]",
                    "worse prop": True
                }
            ])

        self.assertIn("has an invalid property: \"worse prop\"", str(assertion.exception))

    def test_command_item_invalid_combinations(self):
        for item1, item2 in [("passthrough", "background"),
                             ("passthrough", "input"),
                             ("passthrough", "diff")]:
            with self.assertRaises(ModelParseError) as assertion:
                parse_commands([
                    {
                        "name": "test",
                        "command": "doge | lolcat",
                        item1: "yup",
                        item2: "yup"
                    }
                ])

            self.assertIn("has both", str(assertion.exception))

    def test_command_item_diff_str(self):
        commands = parse_commands([
            {
                "name": "tester",
                "command": "yes GRADEFAST IS AWESOME",
                "diff": "yes.out"
            }
        ])
        self.assertListEqual(commands, [
            CommandItem(
                name="tester",
                command="yes GRADEFAST IS AWESOME",
                diff=CommandItem.Diff(file="yes.out")
            )
        ])

    def test_command_item_diff_dict(self):
        commands = parse_commands([
            {
                "name": "test with content",
                "command": "echo test 1",
                "diff": {
                    "content": "test 1"
                }
            },
            {
                "name": "test with file",
                "command": "echo test 2",
                "diff": {
                    "file": "test2.out"
                }
            },
            {
                "name": "test with submission file",
                "command": "echo test 3",
                "diff": {
                    "submission file": "test3.out"
                }
            },
            {
                "name": "test with command",
                "command": "echo test 4",
                "diff": {
                    "command": "echo test 4"
                }
            }
        ])
        self.assertListEqual(commands, [
            CommandItem(
                name="test with content",
                command="echo test 1",
                diff=CommandItem.Diff(content="test 1")
            ),
            CommandItem(
                name="test with file",
                command="echo test 2",
                diff=CommandItem.Diff(file="test2.out")
            ),
            CommandItem(
                name="test with submission file",
                command="echo test 3",
                diff=CommandItem.Diff(submission_file="test3.out")
            ),
            CommandItem(
                name="test with command",
                command="echo test 4",
                diff=CommandItem.Diff(command="echo test 4")
            )
        ])

    def test_command_item_diff_options(self):
        commands = parse_commands([
            {
                "name": "test with collapse whitespace",
                "command": "echo \"\tw h i t e \n\t s p a c e\"",
                "diff": {
                    "content": "whitespace",
                    "collapse whitespace": True
                }
            },
            {
                "name": "test without collapse whitespace",
                "command": "echo \"\tw h i t e \n\t s p a c e\"",
                "diff": {
                    "content": "\tw h i t e \n\t s p a c e",
                    "collapse whitespace": False
                }
            }
        ])
        self.assertListEqual(commands, [
            CommandItem(
                name="test with collapse whitespace",
                command="echo \"\tw h i t e \n\t s p a c e\"",
                diff=CommandItem.Diff(
                    content="whitespace",
                    collapse_whitespace=True
                )
            ),
            CommandItem(
                name="test without collapse whitespace",
                command="echo \"\tw h i t e \n\t s p a c e\"",
                diff=CommandItem.Diff(
                    content="\tw h i t e \n\t s p a c e",
                    collapse_whitespace=False
                )
            )
        ])

    def test_command_item_diff_invalid_properties(self):
        with self.assertRaises(ModelParseError) as assertion:
            parse_commands([
                {
                    "name": "test",
                    "command": "",
                    "diff": {
                        "content": "",
                        "bad prop": "abc"
                    }
                }
            ])

        self.assertIn("diff object has an invalid property: \"bad prop\"", str(assertion.exception))
