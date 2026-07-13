const { withSettingsGradle } = require("expo/config-plugins");

const JITPACK_URL = "https://jitpack.io";
const JITPACK_REPOSITORY = `\n        maven { url \"${JITPACK_URL}\" }`;

module.exports = function withTesseractJitPack(config) {
  return withSettingsGradle(config, (settingsConfig) => {
    const contents = settingsConfig.modResults.contents;
    if (contents.includes(JITPACK_URL)) {
      return settingsConfig;
    }

    const dependencyResolutionIndex = contents.indexOf("dependencyResolutionManagement");
    if (dependencyResolutionIndex < 0) {
      return settingsConfig;
    }

    const repositoriesIndex = contents.indexOf("repositories {", dependencyResolutionIndex);
    if (repositoriesIndex < 0) {
      return settingsConfig;
    }

    const insertionIndex = repositoriesIndex + "repositories {".length;
    settingsConfig.modResults.contents =
      contents.slice(0, insertionIndex) + JITPACK_REPOSITORY + contents.slice(insertionIndex);

    return settingsConfig;
  });
};
