from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_ui.application import default_paths


class DefaultPathsTests(unittest.TestCase):
    def test_user_patterns_path_is_inside_cache_dir(self) -> None:
        with patch.object(default_paths, "app_cache_dir", return_value=Path("/tmp/cache")):
            self.assertEqual(
                default_paths.user_patterns_path(),
                Path("/tmp/cache/patterns.json"),
            )

    def test_resolve_patterns_path_seeds_from_default(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache_dir = base / "cache"
            cache_dir.mkdir()
            seed = base / "patterns.json"
            seed.write_text('{"patterns": {"ER1": "\\\\d+"}}', encoding="utf-8")

            with patch.object(default_paths, "app_cache_dir", return_value=cache_dir), patch.object(
                default_paths, "default_patterns_seed_path", return_value=seed
            ):
                target = default_paths.resolve_patterns_path()

            self.assertEqual(target, cache_dir / "patterns.json")
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), seed.read_text(encoding="utf-8"))

    def test_resolve_patterns_path_keeps_existing_user_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache_dir = base / "cache"
            cache_dir.mkdir()
            existing = cache_dir / "patterns.json"
            existing.write_text("USER_EDITED", encoding="utf-8")
            seed = base / "patterns.json"
            seed.write_text("SEED", encoding="utf-8")

            with patch.object(default_paths, "app_cache_dir", return_value=cache_dir), patch.object(
                default_paths, "default_patterns_seed_path", return_value=seed
            ):
                target = default_paths.resolve_patterns_path()

            self.assertEqual(target.read_text(encoding="utf-8"), "USER_EDITED")


if __name__ == "__main__":
    unittest.main()
