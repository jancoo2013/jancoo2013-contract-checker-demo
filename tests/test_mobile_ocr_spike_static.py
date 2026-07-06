import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile"


class MobileOcrSpikeStaticTests(unittest.TestCase):
    def test_app_config_disables_backup_and_blocks_storage_permissions(self) -> None:
        config = json.loads((MOBILE / "app.json").read_text(encoding="utf-8"))
        android = config["expo"]["android"]

        self.assertIs(android["allowBackup"], False)
        self.assertEqual(android["permissions"], [])
        self.assertIn("android.permission.READ_EXTERNAL_STORAGE", android["blockedPermissions"])
        self.assertIn("android.permission.WRITE_EXTERNAL_STORAGE", android["blockedPermissions"])

    def test_local_ocr_module_is_android_only_and_bundles_hebrew_model(self) -> None:
        module_config = json.loads(
            (MOBILE / "modules" / "local-ocr" / "expo-module.config.json").read_text(
                encoding="utf-8"
            )
        )
        build_gradle = (
            MOBILE / "modules" / "local-ocr" / "android" / "build.gradle"
        ).read_text(encoding="utf-8")
        traineddata = (
            MOBILE
            / "modules"
            / "local-ocr"
            / "android"
            / "src"
            / "main"
            / "assets"
            / "tessdata"
            / "heb.traineddata"
        )

        self.assertEqual(module_config["platforms"], ["android"])
        self.assertIn("expo-module-gradle-plugin", build_gradle)
        self.assertNotIn("ExpoModulesCorePlugin.gradle", build_gradle)
        self.assertIn("tesseract4android:4.9.0", build_gradle)
        self.assertTrue(traineddata.exists())
        self.assertGreater(traineddata.stat().st_size, 100_000)

    def test_generated_native_directories_are_ignored(self) -> None:
        gitignore = (MOBILE / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("android/", gitignore)
        self.assertIn("ios/", gitignore)

    def test_local_ocr_experiment_stays_local(self) -> None:
        experiment = (MOBILE / "src" / "LocalOcrExperiment.tsx").read_text(encoding="utf-8")

        self.assertIn("Run local OCR", experiment)
        self.assertIn("LocalOcr.recognizeBundledImage", experiment)
        self.assertNotIn("fetch(", experiment)
        self.assertNotIn("GoogleGenerativeAI", experiment)
        self.assertNotIn("generateContent", experiment)
        self.assertIn("synthetic-hebrew-pii.png", experiment)
        self.assertIn("synthetic-hebrew-layout.png", experiment)


if __name__ == "__main__":
    unittest.main()
