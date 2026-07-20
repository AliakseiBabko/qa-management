import unittest
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
            with self.assertRaisesRegex(SystemExit, "is inside the synchronized Drive workspace"):
                assert_private_mirror(mirror_dir, data_root, init_allowed=True)

if __name__ == '__main__':
    unittest.main()
