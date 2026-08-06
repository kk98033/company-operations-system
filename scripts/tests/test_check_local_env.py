import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check-local-env.sh"


class CheckLocalEnvTests(unittest.TestCase):
    def run_check(self, content: str | None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_path = Path(temporary_directory) / ".env"
            if content is not None:
                env_path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [str(CHECK_SCRIPT), str(env_path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_accepts_non_placeholder_password_without_echoing_it(self) -> None:
        result = self.run_check("POSTGRES_PASSWORD=local-secret-canary\n")

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("local-secret-canary", result.stdout + result.stderr)

    def test_rejects_missing_empty_and_placeholder_passwords(self) -> None:
        for content in (
            None,
            "APP_ENV=development\n",
            "POSTGRES_PASSWORD=\n",
            "POSTGRES_PASSWORD=   \n",
            "POSTGRES_PASSWORD=\"\"\n",
            "POSTGRES_PASSWORD='   '\n",
            "POSTGRES_PASSWORD=replace-with-local-only-password\n",
            "POSTGRES_PASSWORD=\"replace-with-local-only-password\"\n",
            "POSTGRES_PASSWORD=replace-with-local-only-password # replace me\n",
        ):
            with self.subTest(content=content):
                result = self.run_check(content)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
