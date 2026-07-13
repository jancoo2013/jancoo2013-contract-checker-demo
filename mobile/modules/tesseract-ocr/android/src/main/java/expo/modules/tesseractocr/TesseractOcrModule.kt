package expo.modules.tesseractocr

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.SystemClock
import android.provider.OpenableColumns
import com.googlecode.tesseract.android.TessBaseAPI
import expo.modules.kotlin.Promise
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.exception.toCodedException
import expo.modules.kotlin.functions.Coroutine
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

private const val PICK_IMAGE_REQUEST_CODE = 7412
private const val HEBREW_LANGUAGE = "heb"
private const val HEBREW_MODEL_FILENAME = "heb.traineddata"
private const val HEBREW_MODEL_URL =
  "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/heb.traineddata"
private const val MIN_MODEL_BYTES = 500_000L
private const val MAX_MODEL_BYTES = 5_000_000L
private const val MAX_IMAGE_PIXELS = 12_000_000L

class TesseractOcrModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  private var pendingPickPromise: Promise? = null

  override fun definition() = ModuleDefinition {
    Name("TesseractOcr")

    AsyncFunction("isModelInstalledAsync") {
      isModelInstalled()
    }

    AsyncFunction("downloadHebrewModelAsync") Coroutine {
      downloadHebrewModel()
    }

    AsyncFunction("pickImageAsync") { promise: Promise ->
      if (pendingPickPromise != null) {
        throw IllegalStateException("An image picker request is already in progress.")
      }

      pendingPickPromise = promise
      val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
        addCategory(Intent.CATEGORY_OPENABLE)
        type = "image/*"
      }
      appContext.throwingActivity.startActivityForResult(intent, PICK_IMAGE_REQUEST_CODE)
    }

    OnActivityResult { _, (requestCode, resultCode, intent) ->
      if (requestCode != PICK_IMAGE_REQUEST_CODE || pendingPickPromise == null) {
        return@OnActivityResult
      }

      val promise = pendingPickPromise!!
      pendingPickPromise = null

      if (resultCode != Activity.RESULT_OK) {
        promise.resolve(mapOf("canceled" to true))
        return@OnActivityResult
      }

      try {
        val sourceUri = intent?.data ?: throw IllegalStateException("The selected image URI is missing.")
        val copiedImage = copyPickedImageToCache(sourceUri)
        val bounds = readImageBounds(copiedImage)
        promise.resolve(
          mapOf(
            "canceled" to false,
            "uri" to Uri.fromFile(copiedImage).toString(),
            "name" to copiedImage.name,
            "width" to bounds.first,
            "height" to bounds.second
          )
        )
      } catch (error: Exception) {
        promise.reject(error.toCodedException())
      }
    }

    AsyncFunction("recognizeAsync") Coroutine { uriString: String ->
      recognize(uriString)
    }
  }

  private fun tesseractRoot(): File = File(context.filesDir, "tesseract")

  private fun modelFile(): File = File(File(tesseractRoot(), "tessdata"), HEBREW_MODEL_FILENAME)

  private fun isModelInstalled(): Boolean {
    val model = modelFile()
    return model.isFile && model.length() in MIN_MODEL_BYTES..MAX_MODEL_BYTES
  }

  private fun downloadHebrewModel(): Map<String, Any> {
    val target = modelFile()
    if (isModelInstalled()) {
      return mapOf(
        "installed" to true,
        "downloaded" to false,
        "bytes" to target.length()
      )
    }

    target.parentFile?.mkdirs()
    val temporary = File(target.parentFile, "$HEBREW_MODEL_FILENAME.part")
    temporary.delete()

    val connection = URL(HEBREW_MODEL_URL).openConnection() as HttpURLConnection
    connection.requestMethod = "GET"
    connection.instanceFollowRedirects = true
    connection.connectTimeout = 15_000
    connection.readTimeout = 60_000
    connection.setRequestProperty("User-Agent", "ContractCheckerAndroidTesseractSpike/0.1")

    try {
      connection.connect()
      if (connection.responseCode !in 200..299) {
        throw IllegalStateException("Hebrew OCR model download failed with HTTP ${connection.responseCode}.")
      }

      connection.inputStream.use { input ->
        FileOutputStream(temporary).use { output ->
          input.copyTo(output)
        }
      }

      if (temporary.length() !in MIN_MODEL_BYTES..MAX_MODEL_BYTES) {
        temporary.delete()
        throw IllegalStateException("Downloaded Hebrew OCR model has an unexpected size.")
      }

      if (target.exists() && !target.delete()) {
        temporary.delete()
        throw IllegalStateException("Unable to replace the existing Hebrew OCR model.")
      }

      if (!temporary.renameTo(target)) {
        temporary.copyTo(target, overwrite = true)
        temporary.delete()
      }

      return mapOf(
        "installed" to true,
        "downloaded" to true,
        "bytes" to target.length()
      )
    } finally {
      connection.disconnect()
      if (temporary.exists() && !target.exists()) {
        temporary.delete()
      }
    }
  }

  private fun copyPickedImageToCache(sourceUri: Uri): File {
    val inputDirectory = File(context.cacheDir, "tesseract-inputs")
    inputDirectory.mkdirs()
    inputDirectory.listFiles()?.forEach { it.delete() }

    val displayName = readDisplayName(sourceUri)
    val extension = displayName
      ?.substringAfterLast('.', missingDelimiterValue = "")
      ?.lowercase()
      ?.takeIf { it.matches(Regex("[a-z0-9]{1,5}")) }
      ?: "img"

    val outputFile = File(inputDirectory, "ocr-input-${System.currentTimeMillis()}.$extension")
    context.contentResolver.openInputStream(sourceUri).use { input ->
      input ?: throw IllegalStateException("Unable to open the selected image.")
      FileOutputStream(outputFile).use { output ->
        input.copyTo(output)
      }
    }

    if (outputFile.length() == 0L) {
      outputFile.delete()
      throw IllegalStateException("The selected image is empty.")
    }

    return outputFile
  }

  private fun readDisplayName(uri: Uri): String? {
    return context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
      ?.use { cursor ->
        if (!cursor.moveToFirst()) {
          return@use null
        }
        val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
        if (index < 0) null else cursor.getString(index)
      }
  }

  private fun readImageBounds(file: File): Pair<Int, Int> {
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, options)
    if (options.outWidth <= 0 || options.outHeight <= 0) {
      throw IllegalStateException("The selected file is not a readable bitmap image.")
    }
    return options.outWidth to options.outHeight
  }

  private fun decodeSampledBitmap(file: File): Bitmap {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
      throw IllegalStateException("The selected file is not a readable bitmap image.")
    }

    var sampleSize = 1
    while (
      (bounds.outWidth.toLong() / sampleSize) * (bounds.outHeight.toLong() / sampleSize) >
      MAX_IMAGE_PIXELS
    ) {
      sampleSize *= 2
    }

    val options = BitmapFactory.Options().apply {
      inSampleSize = sampleSize
      inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return BitmapFactory.decodeFile(file.absolutePath, options)
      ?: throw IllegalStateException("Unable to decode the selected image.")
  }

  private fun materializeImage(uriString: String): File {
    val uri = Uri.parse(uriString)
    if (uri.scheme == null || uri.scheme == "file") {
      val path = uri.path ?: uriString
      val file = File(path)
      if (!file.isFile) {
        throw IllegalStateException("The selected image file does not exist.")
      }
      return file
    }

    if (uri.scheme == "content") {
      return copyPickedImageToCache(uri)
    }

    throw IllegalArgumentException("Only local file and content image URIs are supported.")
  }

  private fun recognize(uriString: String): Map<String, Any> {
    if (!isModelInstalled()) {
      throw IllegalStateException("The Hebrew OCR model is not installed.")
    }

    val imageFile = materializeImage(uriString)
    val bitmap = decodeSampledBitmap(imageFile)
    val startedAt = SystemClock.elapsedRealtime()
    val tesseract = TessBaseAPI()

    try {
      if (!tesseract.init(tesseractRoot().absolutePath, HEBREW_LANGUAGE)) {
        throw IllegalStateException("Tesseract failed to initialize the Hebrew language model.")
      }

      tesseract.setPageSegMode(TessBaseAPI.PageSegMode.PSM_AUTO)
      tesseract.setVariable("preserve_interword_spaces", "1")
      tesseract.setImage(bitmap)

      val text = tesseract.getUTF8Text().orEmpty()
      val elapsedMs = SystemClock.elapsedRealtime() - startedAt
      return mapOf(
        "text" to text,
        "elapsedMs" to elapsedMs,
        "meanConfidence" to tesseract.meanConfidence(),
        "width" to bitmap.width,
        "height" to bitmap.height
      )
    } finally {
      tesseract.recycle()
      bitmap.recycle()
    }
  }
}
