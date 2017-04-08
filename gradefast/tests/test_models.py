import unittest

from gradefast.models import Path


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
