import unittest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from mirror_common import assert_private_mirror

class TestMirrorCommon(unittest.TestCase):
    def test_assert_private_mirror_new_dir(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mirror_dir = tmp_path / "mirror"
            data_root = tmp_path / "data"
            data_root.mkdir()
            # Should create mirror_dir
            assert_private_mirror(mirror_dir, data_root, init_allowed=True)
            pass
            pass

    def test_assert_private_mirror_existing_empty(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mirror_dir = tmp_path / "mirror"
            mirror_dir.mkdir()
            data_root = tmp_path / "data"
            data_root.mkdir()
            assert_private_mirror(mirror_dir, data_root, init_allowed=True)
            pass

    def test_assert_private_mirror_existing_non_empty_no_git(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mirror_dir = tmp_path / "mirror"
            mirror_dir.mkdir()
            (mirror_dir / "foo.txt").write_text("hello")
            data_root = tmp_path / "data"
            data_root.mkdir()
            with self.assertRaisesRegex(SystemExit, "exists and is not empty before initialization"):
                assert_private_mirror(mirror_dir, data_root, init_allowed=True)

    def test_assert_private_mirror_inside_data_root(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data_root = tmp_path / "data"
            data_root.mkdir()
            mirror_dir = data_root / "mirror"
            with self.assertRaisesRegex(SystemExit, "overlaps with the synchronized Drive workspace"):
                assert_private_mirror(mirror_dir, data_root, init_allowed=True)


    def test_mirror_security_wrong_toplevel(self):
        import mirror_common
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mirror_dir = tmp_path / "mirror"
            mirror_dir.mkdir()
            data_root = tmp_path / "data"
            data_root.mkdir()
            mirror_common.mirror_git(mirror_dir, "init")
            sub = mirror_dir / "sub"
            sub.mkdir()
            with self.assertRaises(SystemExit):
                mirror_common.assert_private_mirror(sub, data_root, init_allowed=False)

    def test_mirror_security_remotes(self):
        import mirror_common
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mirror_dir = tmp_path / "mirror"
            mirror_dir.mkdir()
            data_root = tmp_path / "data"
            data_root.mkdir()
            mirror_common.mirror_git(mirror_dir, "init")
            mirror_common.mirror_git(mirror_dir, "remote", "add", "origin", "https://github.com/test/test.git")
            with self.assertRaises(SystemExit):
                mirror_common.assert_private_mirror(mirror_dir, data_root, init_allowed=False)

    def test_mirror_security_public_overlap(self):
        import mirror_common
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data_root = tmp_path / "data"
            data_root.mkdir()
            skills_repo = Path(__file__).resolve().parents[2]
            with self.assertRaises(SystemExit):
                mirror_common.assert_private_mirror(skills_repo, data_root, init_allowed=False)

if __name__ == '__main__':
    unittest.main()
