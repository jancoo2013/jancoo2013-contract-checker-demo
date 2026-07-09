package com.jancoo.contractchecker.localocr

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.SystemClock
import com.googlecode.tesseract.android.TessBaseAPI
import com.googlecode.tesseract.android.TessBaseAPI.PageIteratorLevel
import expo.modules.kotlin.Promise
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.Closeable
import java.io.File

class LocalOcrModule : Module() {
  private var pendingPickPromise: Promise? = null

  override fun definition() = ModuleDefinition {
    Name("LocalOcr")

    AsyncFunction("recognizeBundledImage") { assetName: String ->
      recognizeBundledImage(assetName)
    }

    AsyncFunction("pickLocalImage") { promise: Promise ->
      pickLocalImage(promise)
    }

    AsyncFunction("recognizeLocalImageUri") { uriString: String ->
      recognizeLocalImageUri(uriString)
    }

    OnActivityResult { _, payload ->
      if (payload.requestCode != LOCAL_IMAGE_PICK_REQUEST_CODE) {
        return@OnActivityResult
      }

      val promise = pendingPickPromise ?: return@OnActivityResult
      pendingPickPromise = null

      if (payload.resultCode != Activity.RESULT_OK) {
        promise.resolve(null)
        return@OnActivityResult
      }

      val uri = payload.data?.data
      if (uri == null) {
        promise.resolve(null)
        return@OnActivityResult
      }

      val scheme = uri.scheme?.lowercase().orEmpty()
      if (!isAllowedLocalImageScheme(scheme)) {
        promise.reject("ERR_LOCAL_OCR_UNSUPPORTED_URI", "Unsupported local image URI scheme.", null)
        return@OnActivityResult
      }

      promise.resolve(mapOf("uri" to uri.toString()))
    }
  }

  private fun recognizeBundledImage(assetName: String): Map<String, Any> {
    val context = appContext.reactContext
      ?: throw IllegalStateException("React context is not available.")
    val safeAssetName = when (assetName) {
      "synthetic-hebrew-pii.png",
      "synthetic-hebrew-pii-large.png",
      "synthetic-hebrew-layout.png" -> assetName
      else -> throw IllegalArgumentException("Unsupported bundled OCR asset.")
    }

    val bitmap = context.assets.open(safeAssetName).use { input ->
      BitmapFactory.decodeStream(input)
    } ?: throw IllegalStateException("Could not decode bundled OCR asset.")

    return recognizeBitmap(context, bitmap)
  }

  private fun pickLocalImage(promise: Promise) {
    val activity = appContext.currentActivity
    if (activity == null) {
      promise.reject("ERR_LOCAL_OCR_NO_ACTIVITY", "Current activity is not available.", null)
      return
    }

    if (pendingPickPromise != null) {
      promise.reject("ERR_LOCAL_OCR_PICK_IN_PROGRESS", "A local image picker request is already in progress.", null)
      return
    }

    pendingPickPromise = promise

    val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
      addCategory(Intent.CATEGORY_OPENABLE)
      type = "image/*"
      addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }

    try {
      activity.startActivityForResult(intent, LOCAL_IMAGE_PICK_REQUEST_CODE)
    } catch (error: Throwable) {
      pendingPickPromise = null
      promise.reject("ERR_LOCAL_OCR_PICK_FAILED", "Could not open local image picker.", error)
    }
  }

  private fun recognizeLocalImageUri(uriString: String): Map<String, Any> {
    val context = appContext.reactContext
      ?: throw IllegalStateException("React context is not available.")
    val uri = Uri.parse(uriString)
    val scheme = uri.scheme?.lowercase().orEmpty()

    if (scheme == "http" || scheme == "https") {
      throw IllegalArgumentException("Remote image URI schemes are not supported.")
    }

    if (!isAllowedLocalImageScheme(scheme)) {
      throw IllegalArgumentException("Unsupported local image URI scheme.")
    }

    val bitmap = context.contentResolver.openInputStream(uri).useIfNotNull { input ->
      BitmapFactory.decodeStream(input)
    } ?: throw IllegalStateException("Could not decode local OCR image.")

    return recognizeBitmap(context, bitmap)
  }

  private fun recognizeBitmap(context: Context, bitmap: android.graphics.Bitmap): Map<String, Any> {
    val dataPath = ensureHebrewTrainedData(context)
    val startedAt = SystemClock.elapsedRealtime()
    val tess = TessBaseAPI()
    try {
      val initialized = tess.init(dataPath.absolutePath, "heb", TessBaseAPI.OEM_LSTM_ONLY)
      if (!initialized) {
        throw IllegalStateException("Could not initialize Hebrew Tesseract data.")
      }

      tess.setDebug(false)
      tess.setPageSegMode(TessBaseAPI.PageSegMode.PSM_AUTO)
      tess.setImage(bitmap)

      val recognizedText = tess.getUTF8Text() ?: ""
      val symbolWords = readSymbolWords(tess)
      val items = readWordItems(tess, symbolWords)
      val durationMs = SystemClock.elapsedRealtime() - startedAt

      return mapOf(
        "text" to recognizedText,
        "width" to bitmap.width,
        "height" to bitmap.height,
        "durationMs" to durationMs,
        "items" to items
      )
    } finally {
      tess.recycle()
      bitmap.recycle()
    }
  }

  private fun isAllowedLocalImageScheme(scheme: String): Boolean {
    return scheme == "content" || scheme == "file"
  }

  private fun ensureHebrewTrainedData(context: Context): File {
    val root = File(context.filesDir, "local_ocr_tesseract")
    val tessdataDir = File(root, "tessdata")
    val target = File(tessdataDir, "heb.traineddata")

    if (!tessdataDir.exists() && !tessdataDir.mkdirs()) {
      throw IllegalStateException("Could not create app-private tessdata directory.")
    }

    val assetPath = "tessdata/heb.traineddata"
    context.assets.open(assetPath).use { source ->
      if (target.exists() && target.length() == source.available().toLong()) {
        return root
      }

      target.outputStream().use { output ->
        source.copyTo(output)
      }
    }

    return root
  }

  private inline fun <T : Closeable, R> T?.useIfNotNull(block: (T) -> R): R? {
    return this?.use(block)
  }

  private fun readSymbolWords(tess: TessBaseAPI): List<String> {
    val iterator = tess.getResultIterator() ?: return emptyList()
    val words = mutableListOf<String>()
    val currentWord = StringBuilder()

    try {
      iterator.begin()

      do {
        if (iterator.isAtBeginningOf(PageIteratorLevel.RIL_WORD) && currentWord.isNotEmpty()) {
          words.add(currentWord.toString())
          currentWord.clear()
        }

        val symbol = iterator.getUTF8Text(PageIteratorLevel.RIL_SYMBOL).orEmpty()
        currentWord.append(symbol)
      } while (iterator.next(PageIteratorLevel.RIL_SYMBOL))

      if (currentWord.isNotEmpty()) {
        words.add(currentWord.toString())
      }
    } finally {
      iterator.delete()
    }

    return words
  }

  private fun readWordItems(
    tess: TessBaseAPI,
    symbolWords: List<String>
  ): List<Map<String, Any>> {
    val iterator = tess.getResultIterator() ?: return emptyList()
    val items = mutableListOf<Map<String, Any>>()
    var wordIndex = 0

    try {
      iterator.begin()

      do {
        val word = iterator.getUTF8Text(PageIteratorLevel.RIL_WORD)?.trim().orEmpty()
        val symbolText = symbolWords.getOrNull(wordIndex).orEmpty()
        val box = iterator.getBoundingBox(PageIteratorLevel.RIL_WORD)
        wordIndex += 1

        if (word.isNotEmpty() && box.size >= 4) {
          items.add(
            mapOf(
              "text" to word,
              "symbolText" to symbolText,
              "confidence" to iterator.confidence(PageIteratorLevel.RIL_WORD),
              "bbox" to mapOf(
                "x" to box[0],
                "y" to box[1],
                "width" to (box[2] - box[0]),
                "height" to (box[3] - box[1])
              )
            )
          )
        }
      } while (iterator.next(PageIteratorLevel.RIL_WORD))
    } finally {
      iterator.delete()
    }

    return items
  }

  private companion object {
    const val LOCAL_IMAGE_PICK_REQUEST_CODE = 9101
  }
}
