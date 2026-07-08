package com.jancoo.contractchecker.localocr

import android.content.Context
import android.graphics.BitmapFactory
import android.os.SystemClock
import com.googlecode.tesseract.android.TessBaseAPI
import com.googlecode.tesseract.android.TessBaseAPI.PageIteratorLevel
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File

class LocalOcrModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("LocalOcr")

    AsyncFunction("recognizeBundledImage") { assetName: String ->
      recognizeBundledImage(assetName)
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

    val dataPath = ensureHebrewTrainedData(context)
    val startedAt = SystemClock.elapsedRealtime()
    val bitmap = context.assets.open(safeAssetName).use { input ->
      BitmapFactory.decodeStream(input)
    } ?: throw IllegalStateException("Could not decode bundled OCR asset.")

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

  private fun readSymbolWords(tess: TessBaseAPI): List<String> {
    val iterator = tess.getResultIterator() ?: return emptyList()
    val words = mutableListOf<String>()
    val currentWord = StringBuilder()

    try {
      iterator.begin()

      do {
        if (iterator.isAtBeginningOf(PageIteratorLevel.RIL_WORD) && currentWord.isNotEmpty()) {
          words.add(currentWord.toString())
          currentWord.setLength(0)
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
}
