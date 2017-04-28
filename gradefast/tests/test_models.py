import unittest

from gradefast.models import Path, SlotEqualityMixin


class TestSlotEqualityMixin(unittest.TestCase):
    class Example(SlotEqualityMixin):
        __slots__ = ("a", "b", "c")

        def __init__(self, a, b, c):
            self.a = a
            self.b = b
            self.c = c

    def test_equality(self):
        example1 = self.Example(1, 2, 3)
        example2 = self.Example(1, 2, 3)
        example3 = self.Example(2, 3, 4)

        self.assertEqual(example1, example2)
        self.assertFalse(example1.__eq__(example3))
        self.assertIs(example1.__eq__(""), NotImplemented)

    def test_inequality(self):
        example1 = self.Example(1, 2, 3)
        example2 = self.Example(1, 2, 3)
        example3 = self.Example(2, 3, 4)

        self.assertNotEqual(example1, example3)
        self.assertFalse(example1.__ne__(example2))
        self.assertNotEqual(example1, "")
        self.assertNotEqual("", example1)

    def test_hash(self):
        example1 = self.Example(1, 2, 3)
        example2 = self.Example(1, 2, 3)
        example3 = self.Example(2, 3, 4)

        self.assertEqual(hash(example1), hash(example2))
        self.assertNotEqual(hash(example1), hash(example3))


class TestPath(unittest.TestCase):
    def test_equality(self):
        self.assertTrue(Path("a/b/c") == Path("a/b/c"))
        self.assertFalse(Path("a/b/c") != Path("a/b/c"))

        self.assertTrue(Path("a/") != Path("a/b"))
        self.assertFalse(Path("a/") == Path("a/b"))

        self.assertTrue(Path("/") != "/")
        self.assertFalse(Path("/") == "/")

        self.assertTrue("/" != Path("/"))
        self.assertFalse("/" == Path("/"))

    def test_append(self):
        base_path = Path("/a/b")
        self.assertEqual(base_path.append("c"), Path("/a/b/c"))
        self.assertEqual(base_path.append("c/d"), Path("/a/b/c/d"))
        self.assertEqual(base_path.append("/c/d"), Path("/a/b/c/d"))
        self.assertEqual(base_path.append("."), Path("/a/b"))
        self.assertEqual(base_path.append("././././"), Path("/a/b"))
        self.assertEqual(base_path.append(".."), Path("/a"))
        self.assertEqual(base_path.append("../.."), Path("/"))
        self.assertEqual(base_path.append("/../../"), Path("/"))
        self.assertEqual(base_path.append("../../.."), Path("/.."))

        base_path = Path("~/grading/project")
        self.assertEqual(base_path.append("student"), Path("~/grading/project/student"))
        self.assertEqual(base_path.append("../project2"), Path("~/grading/project2"))
        self.assertEqual(base_path.append("../project2/stud"), Path("~/grading/project2/stud"))
        self.assertEqual(base_path.append("../../Videos/"), Path("~/Videos"))
        self.assertEqual(base_path.append("../../../user2"), Path("~/../user2"))
        self.assertEqual(base_path.append("../../../user2/personal"), Path("~/../user2/personal"))
        self.assertEqual(base_path.append("../../../.."), Path("~/../.."))
        self.assertEqual(base_path.append("../../../../root"), Path("~/../../root"))

        base_path = Path("~")
        self.assertEqual(base_path.append("../"), Path("~/.."))

    def test_relative_str(self):
        self.assertEqual(Path("~/grading/project").relative_str(Path("~")), "grading/project")
        self.assertEqual(Path("~/grading/project").relative_str(Path("~/")), "grading/project")
        self.assertEqual(Path("~/grading").relative_str(Path("nope")), "~/grading")
        self.assertEqual(Path("~/../a").relative_str(Path("~")), "~/../a")


if __name__ == "__main__":
    unittest.main()
