import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from zipfile import ZipFile


VERIFIER = Path(__file__).resolve().parents[1] / "scripts" / "verify-apk.sh"
CERTIFICATE_DIGEST = hashlib.sha256(b"release certificate").hexdigest()


class VerifyApkTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        apk = self.root / "build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
        apk.parent.mkdir(parents=True)
        with ZipFile(apk, "w") as archive:
            archive.writestr("lib/arm64-v8a/libimmich.so", b"")

        self.tools = self.root / "sdk/build-tools/37.0.0"
        self.tools.mkdir(parents=True)
        self.write_tool(
            "aapt",
            """printf '%s\n' "package: name='app.alextran.immich.personal' versionCode='1'" "application-label:'Immich'"
""",
        )
        self.write_tool("apksigner", """printf '%s\n' "$APKSIGNER_REPORT"\n""")
        self.write_tool("keytool", """printf '%s' 'release certificate' > "${@: -1}"\n""")

    def write_tool(self, name, contents):
        tool = self.tools / name
        tool.write_text("#!/usr/bin/env bash\n" + contents)
        tool.chmod(0o755)

    def verify(self, *report_lines):
        env = os.environ | {
            "ANDROID_SDK_ROOT": str(self.root / "sdk"),
            "PATH": f"{self.tools}:{os.environ['PATH']}",
            "ALIAS": "test",
            "ANDROID_STORE_PASSWORD": "test",
            "APKSIGNER_REPORT": "\n".join(report_lines),
        }
        return subprocess.run(["bash", VERIFIER], cwd=self.root, env=env, capture_output=True, text=True)

    def test_accepts_numbered_signers(self):
        result = self.verify(f"Signer #1 certificate SHA-256 digest: {CERTIFICATE_DIGEST}")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_accepts_the_same_signer_across_schemes(self):
        result = self.verify(
            f"V2 Signer: certificate SHA-256 digest: {CERTIFICATE_DIGEST}",
            f"V3.0 Signer: certificate SHA-256 digest: {CERTIFICATE_DIGEST}",
            f"Source Stamp Signer certificate SHA-256 digest: {'0' * 64}",
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_a_different_signer_in_any_scheme(self):
        result = self.verify(
            f"V2 Signer: certificate SHA-256 digest: {CERTIFICATE_DIGEST}",
            f"V3.0 Signer: certificate SHA-256 digest: {'0' * 64}",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match the configured release certificate", result.stderr)

    def test_rejects_a_missing_apk_signer(self):
        result = self.verify(f"Source Stamp Signer certificate SHA-256 digest: {CERTIFICATE_DIGEST}")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No APK signer certificate", result.stderr)
