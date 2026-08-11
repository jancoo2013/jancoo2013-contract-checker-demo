package expo.modules.documentgeometrypreview

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Matrix
import android.graphics.Paint
import android.media.ExifInterface
import android.net.Uri
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.functions.Coroutine
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File
import java.io.FileOutputStream
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.round
import kotlin.math.roundToInt
import kotlin.math.sin

private const val PREVIEW_LONG_SIDE = 1800
private const val MAX_SOURCE_LONG_SIDE = 8192
private const val MAX_SOURCE_PIXELS = 32_000_000L
private const val MAX_SOURCE_BYTES = 48L * 1024L * 1024L
private const val ANALYSIS_LONG_SIDE = 900
private const val MAX_ABS_TEXT_ANGLE_DEGREES = 12
private const val MIN_FOREGROUND_RATIO = 0.0005
private const val MAX_FOREGROUND_RATIO = 0.22
private const val MIN_CONFIDENCE = 0.45
private const val MIN_PROJECTION_GAIN = 0.18
private const val MIN_PEAK_MARGIN = 0.04
private const val MAX_DESKEW_OUTPUT_LONG_SIDE = 10_000
private const val MAX_DESKEW_ACCOUNTED_BYTES = 384L * 1024L * 1024L
private const val MAX_DESKEW_OUTPUT_BYTES = 64L * 1024L * 1024L
private const val DESKEW_JPEG_QUALITY = 95

private data class TransformAngle(
  val rotationDegrees: Double,
  val fallbackReasons: List<String>,
)

class DocumentGeometryPreviewModule : Module() {
  private val context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  private var previewSourceUri: String? = null

  override fun definition() = ModuleDefinition {
    Name("DocumentGeometryPreview")
    AsyncFunction("buildPreviewAsync") Coroutine { uriString: String -> buildPreview(uriString) }
    AsyncFunction("estimateAngleAsync") Coroutine { previewUri: String -> estimateAngle(previewUri) }
    AsyncFunction("estimateContentRegionAsync") Coroutine { previewUri: String -> estimateContentRegion(previewUri) }
    AsyncFunction("applyFullFrameDeskewAsync") Coroutine { uriString: String, previewUri: String ->
      applyFullFrameDeskew(uriString, previewUri)
    }
  }

  private fun cacheRoot(): File = File(context.cacheDir, "document-geometry-preview")

  private fun prepareCache(): File {
    previewSourceUri = null
    val root = cacheRoot()
    root.deleteRecursively()
    if (!root.mkdirs() && !root.isDirectory) {
      throw IllegalStateException("Unable to create geometry preview cache.")
    }
    return root
  }

  private fun materializeLocalImage(uriString: String, root: File): File {
    val uri = Uri.parse(uriString)
    if (uri.scheme == null || uri.scheme == "file") {
      val file = File(uri.path ?: uriString)
      if (!file.isFile || file.length() <= 0L || file.length() > MAX_SOURCE_BYTES) {
        throw IllegalArgumentException("Local image is missing, empty, or too large.")
      }
      return file
    }
    if (uri.scheme != "content") {
      throw IllegalArgumentException("Only local file and content image URIs are supported.")
    }

    val target = File(root, "source.img")
    context.contentResolver.openInputStream(uri).use { input ->
      input ?: throw IllegalArgumentException("Unable to open the selected local image.")
      FileOutputStream(target).use { output ->
        val buffer = ByteArray(64 * 1024)
        var total = 0L
        while (true) {
          val count = input.read(buffer)
          if (count < 0) break
          total += count
          if (total > MAX_SOURCE_BYTES) {
            throw IllegalArgumentException("Local image exceeds the bounded byte limit.")
          }
          output.write(buffer, 0, count)
        }
      }
    }
    if (!target.isFile || target.length() <= 0L) {
      throw IllegalArgumentException("The selected local image is empty.")
    }
    return target
  }

  private fun readBounds(file: File): Pair<Int, Int> {
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, options)
    val width = options.outWidth
    val height = options.outHeight
    if (width <= 0 || height <= 0) {
      throw IllegalArgumentException("The selected file is not a readable bitmap image.")
    }
    if (max(width, height) > MAX_SOURCE_LONG_SIDE || width.toLong() * height > MAX_SOURCE_PIXELS) {
      throw IllegalArgumentException("Image exceeds the bounded geometry preview dimensions.")
    }
    return width to height
  }

  private fun readExifOrientation(file: File): Int =
    ExifInterface(file.absolutePath).getAttributeInt(
      ExifInterface.TAG_ORIENTATION,
      ExifInterface.ORIENTATION_NORMAL,
    )

  private fun decodePreviewSource(file: File, width: Int, height: Int): Bitmap {
    var sample = 1
    while (max(width, height) / (sample * 2) >= PREVIEW_LONG_SIDE) sample *= 2
    val options = BitmapFactory.Options().apply {
      inSampleSize = sample
      inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return BitmapFactory.decodeFile(file.absolutePath, options)
      ?: throw IllegalArgumentException("Unable to decode the selected image.")
  }

  private fun decodeFullResolution(file: File): Bitmap {
    val options = BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888 }
    return BitmapFactory.decodeFile(file.absolutePath, options)
      ?: throw IllegalArgumentException("Unable to decode the bounded full-resolution image.")
  }

  private fun orient(bitmap: Bitmap, orientation: Int): Bitmap {
    val matrix = Matrix()
    when (orientation) {
      ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.setScale(-1f, 1f)
      ExifInterface.ORIENTATION_ROTATE_180 -> matrix.setRotate(180f)
      ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.setScale(1f, -1f)
      ExifInterface.ORIENTATION_TRANSPOSE -> {
        matrix.setRotate(90f); matrix.postScale(-1f, 1f)
      }
      ExifInterface.ORIENTATION_ROTATE_90 -> matrix.setRotate(90f)
      ExifInterface.ORIENTATION_TRANSVERSE -> {
        matrix.setRotate(-90f); matrix.postScale(-1f, 1f)
      }
      ExifInterface.ORIENTATION_ROTATE_270 -> matrix.setRotate(-90f)
      ExifInterface.ORIENTATION_NORMAL, ExifInterface.ORIENTATION_UNDEFINED -> return bitmap
      else -> throw IllegalArgumentException("Unsupported EXIF orientation value.")
    }
    val oriented = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    if (oriented !== bitmap) bitmap.recycle()
    return oriented
  }

  private fun scaleToPreview(bitmap: Bitmap, sourceWidth: Int, sourceHeight: Int): Bitmap {
    val scale = minOf(1.0, PREVIEW_LONG_SIDE.toDouble() / max(sourceWidth, sourceHeight))
    val width = max(1, (sourceWidth * scale).roundToInt())
    val height = max(1, (sourceHeight * scale).roundToInt())
    if (bitmap.width == width && bitmap.height == height) return bitmap
    val scaled = Bitmap.createScaledBitmap(bitmap, width, height, true)
    if (scaled !== bitmap) bitmap.recycle()
    return scaled
  }

  private fun grayscale(bitmap: Bitmap): Bitmap {
    val output = Bitmap.createBitmap(bitmap.width, bitmap.height, Bitmap.Config.ARGB_8888)
    val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG).apply {
      colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setSaturation(0f) })
    }
    Canvas(output).drawBitmap(bitmap, 0f, 0f, paint)
    bitmap.recycle()
    return output
  }

  private fun ownedPreview(previewUri: String): Bitmap {
    val uri = Uri.parse(previewUri)
    if (uri.scheme != "file") throw IllegalArgumentException("Geometry preview must be a local file URI.")
    val root = cacheRoot().canonicalFile
    val file = File(uri.path ?: throw IllegalArgumentException("Geometry preview path is missing.")).canonicalFile
    if (file.parentFile != root || file.name != "preview.png" || !file.isFile || file.length() <= 0L) {
      throw IllegalArgumentException("Geometry preview is outside the module-owned cache contract.")
    }
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, options)
    if (
      options.outWidth <= 0 || options.outHeight <= 0 ||
      max(options.outWidth, options.outHeight) > PREVIEW_LONG_SIDE ||
      options.outWidth.toLong() * options.outHeight > PREVIEW_LONG_SIDE.toLong() * PREVIEW_LONG_SIDE
    ) {
      throw IllegalArgumentException("Geometry preview exceeds the bounded angle-estimator contract.")
    }
    return BitmapFactory.decodeFile(file.absolutePath)
      ?: throw IllegalArgumentException("Unable to decode the bounded geometry preview.")
  }

  private fun boxBackground(gray: IntArray, width: Int, height: Int, radius: Int): IntArray {
    val horizontal = IntArray(gray.size)
    val background = IntArray(gray.size)
    val prefix = IntArray(max(width, height) + 1)
    for (y in 0 until height) {
      val row = y * width
      prefix[0] = 0
      for (x in 0 until width) prefix[x + 1] = prefix[x] + gray[row + x]
      for (x in 0 until width) {
        val left = max(0, x - radius)
        val right = min(width - 1, x + radius)
        horizontal[row + x] = (prefix[right + 1] - prefix[left]) / (right - left + 1)
      }
    }
    for (x in 0 until width) {
      prefix[0] = 0
      for (y in 0 until height) prefix[y + 1] = prefix[y] + horizontal[y * width + x]
      for (y in 0 until height) {
        val top = max(0, y - radius)
        val bottom = min(height - 1, y + radius)
        background[y * width + x] = (prefix[bottom + 1] - prefix[top]) / (bottom - top + 1)
      }
    }
    return background
  }

  private fun valueAtRank(histogram: IntArray, rank: Int): Int {
    var seen = 0
    for (value in histogram.indices) {
      seen += histogram[value]
      if (rank < seen) return value
    }
    return histogram.lastIndex
  }

  private fun percentile(histogram: IntArray, count: Int, quantile: Double): Double {
    if (count <= 1) return valueAtRank(histogram, 0).toDouble()
    val position = (count - 1) * quantile
    val lowerRank = position.toInt()
    val upperRank = ceil(position).toInt()
    val lower = valueAtRank(histogram, lowerRank).toDouble()
    val upper = valueAtRank(histogram, upperRank).toDouble()
    return lower + (upper - lower) * (position - lowerRank)
  }

  private fun buildAnalysisMask(preview: Bitmap, longSide: Int = ANALYSIS_LONG_SIDE): Pair<Bitmap, Double> {
    if (longSide !in 1..PREVIEW_LONG_SIDE) throw IllegalArgumentException("Invalid geometry analysis long side.")
    val width = preview.width
    val height = preview.height
    val pixels = IntArray(width * height)
    preview.getPixels(pixels, 0, width, 0, 0, width, height)
    val gray = IntArray(pixels.size) { Color.red(pixels[it]) }
    val radius = max(5, (min(width, height) * 0.012).roundToInt())
    val background = boxBackground(gray, width, height, radius)
    val contrasts = ByteArray(gray.size)
    val histogram = IntArray(256)
    for (index in gray.indices) {
      val contrast = max(0, background[index] - gray[index]).coerceAtMost(255)
      contrasts[index] = contrast.toByte()
      histogram[contrast] += 1
    }
    val median = percentile(histogram, contrasts.size, 0.5)
    val doubledMedian = (median * 2.0).roundToInt()
    val deviationHistogram = IntArray(511)
    for (value in histogram.indices) {
      deviationHistogram[abs(value * 2 - doubledMedian)] += histogram[value]
    }
    val mad = percentile(deviationHistogram, contrasts.size, 0.5) / 2.0
    val p92 = percentile(histogram, contrasts.size, 0.92)
    val threshold = min(48.0, max(9.0, max(median + 4.0 * max(mad, 1.0), p92 * 0.42)))

    var foreground = 0
    for (index in contrasts.indices) {
      val isInk = (contrasts[index].toInt() and 0xff) >= threshold
      pixels[index] = if (isInk) Color.BLACK else Color.WHITE
      if (isInk) foreground += 1
    }
    var mask = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    mask.setPixels(pixels, 0, width, 0, 0, width, height)
    val scale = minOf(1.0, longSide.toDouble() / max(width, height))
    if (scale < 1.0) {
      val scaled = Bitmap.createScaledBitmap(
        mask,
        max(1, (width * scale).roundToInt()),
        max(1, (height * scale).roundToInt()),
        false,
      )
      mask.recycle()
      mask = scaled
    }
    return mask to foreground.toDouble() / contrasts.size.toDouble()
  }

  private fun projectionScore(mask: Bitmap, angleDegrees: Int, work: Bitmap, pixels: IntArray): Double {
    work.eraseColor(Color.WHITE)
    val canvas = Canvas(work)
    val save = canvas.save()
    // Android positive rotation is visually clockwise; negate to preserve the frozen Python sign contract.
    canvas.rotate(-angleDegrees.toFloat(), mask.width / 2f, mask.height / 2f)
    canvas.drawBitmap(mask, 0f, 0f, Paint().apply { isFilterBitmap = false; isAntiAlias = false })
    canvas.restoreToCount(save)
    work.getPixels(pixels, 0, work.width, 0, 0, work.width, work.height)
    var total = 0.0
    var squared = 0.0
    for (y in 0 until work.height) {
      var row = 0
      val start = y * work.width
      for (x in 0 until work.width) {
        if ((pixels[start + x] and 0x00ffffff) == 0) row += 1
      }
      total += row
      squared += row.toDouble() * row.toDouble()
    }
    return if (total <= 0.0) 0.0 else squared / (total * total) * work.height
  }

  private fun rounded(value: Double, digits: Int): Double {
    val factor = if (digits == 8) 100_000_000.0 else 10_000.0
    return round(value * factor) / factor
  }

  private fun estimateAngle(previewUri: String): Map<String, Any> {
    val preview = ownedPreview(previewUri)
    val (mask, foregroundRatio) = try {
      buildAnalysisMask(preview)
    } finally {
      preview.recycle()
    }
    val work = Bitmap.createBitmap(mask.width, mask.height, Bitmap.Config.ARGB_8888)
    val pixels = IntArray(mask.width * mask.height)
    try {
      val scores = (-MAX_ABS_TEXT_ANGLE_DEGREES..MAX_ABS_TEXT_ANGLE_DEGREES).associateWith {
        projectionScore(mask, it, work, pixels)
      }
      var bestRotation = 0
      var bestScore = -1.0
      for ((angle, score) in scores) {
        if (score > bestScore || (score == bestScore && abs(angle) < abs(bestRotation))) {
          bestRotation = angle
          bestScore = score
        }
      }
      val sortedScores = scores.values.sorted()
      val medianScore = sortedScores[sortedScores.size / 2]
      val projectionGain = if (bestScore <= 0.0) 0.0 else max(0.0, (bestScore - medianScore) / bestScore)
      val secondScore = scores.filterKeys { abs(it - bestRotation) > 1 }.values.maxOrNull() ?: 0.0
      val peakMargin = if (bestScore <= 0.0) 0.0 else max(0.0, (bestScore - secondScore) / bestScore)
      val confidence = min(1.0, 1.15 * projectionGain + 0.75 * peakMargin)
      val reasons = mutableSetOf<String>()
      if (foregroundRatio < MIN_FOREGROUND_RATIO) reasons += "insufficient_foreground"
      if (foregroundRatio > MAX_FOREGROUND_RATIO) reasons += "excessive_foreground"
      if (projectionGain < MIN_PROJECTION_GAIN) reasons += "unstable_projection"
      if (peakMargin < MIN_PEAK_MARGIN) reasons += "ambiguous_angle_peak"
      if (abs(bestRotation) == MAX_ABS_TEXT_ANGLE_DEGREES) reasons += "angle_at_search_limit"
      if (confidence < MIN_CONFIDENCE) reasons += "low_confidence"
      return mapOf(
        "dominantTextAngleDegrees" to -bestRotation.toDouble(),
        "deskewRotationDegrees" to bestRotation.toDouble(),
        "confidence" to rounded(confidence, 4),
        "decision" to if (reasons.isEmpty()) "accepted" else "rejected",
        "rejectionReasons" to reasons.sorted(),
        "foregroundRatio" to rounded(foregroundRatio, 8),
        "projectionGain" to rounded(projectionGain, 4),
        "peakMargin" to rounded(peakMargin, 4),
      )
    } finally {
      work.recycle()
      mask.recycle()
    }
  }

  private fun estimateContentRegion(previewUri: String): Map<String, Any?> {
    val angle = estimateAngle(previewUri)
    val decision = angle["decision"] as? String
      ?: throw IllegalStateException("Angle estimator returned an invalid decision.")
    val rotation = (angle["deskewRotationDegrees"] as? Number)?.toDouble()
      ?: throw IllegalStateException("Angle estimator returned an invalid rotation.")
    val preview = ownedPreview(previewUri)
    val mask = try {
      buildAnalysisMask(preview, PREVIEW_LONG_SIDE).first
    } finally {
      preview.recycle()
    }
    return try {
      ContentRegionEstimator.estimate(mask, rotation, decision)
    } finally {
      mask.recycle()
    }
  }

  private fun validatedTransformAngle(previewUri: String): TransformAngle {
    val estimate = estimateAngle(previewUri)
    val decision = estimate["decision"] as? String
      ?: throw IllegalStateException("Angle estimator returned an invalid decision.")
    val rotation = (estimate["deskewRotationDegrees"] as? Number)?.toDouble()
      ?: throw IllegalStateException("Angle estimator returned an invalid rotation.")
    val dominant = (estimate["dominantTextAngleDegrees"] as? Number)?.toDouble()
      ?: throw IllegalStateException("Angle estimator returned an invalid dominant angle.")
    val confidence = (estimate["confidence"] as? Number)?.toDouble()
      ?: throw IllegalStateException("Angle estimator returned an invalid confidence.")
    val reasons = (estimate["rejectionReasons"] as? List<*>)?.map {
      it as? String ?: throw IllegalStateException("Angle estimator returned an invalid rejection reason.")
    } ?: throw IllegalStateException("Angle estimator returned invalid rejection reasons.")

    if (!rotation.isFinite() || abs(rotation) > MAX_ABS_TEXT_ANGLE_DEGREES) {
      throw IllegalStateException("Angle estimator rotation violates the bounded transform contract.")
    }
    if (!dominant.isFinite() || !confidence.isFinite() || confidence !in 0.0..1.0) {
      throw IllegalStateException("Angle estimator returned non-finite transform evidence.")
    }
    if (decision == "accepted") {
      if (
        abs(rotation) >= MAX_ABS_TEXT_ANGLE_DEGREES ||
        confidence < MIN_CONFIDENCE ||
        reasons.isNotEmpty() ||
        abs(dominant + rotation) > 1e-6
      ) {
        throw IllegalStateException("Accepted angle contract is contradictory.")
      }
      return TransformAngle(rotationDegrees = rotation, fallbackReasons = emptyList())
    }
    if (decision == "rejected") {
      return TransformAngle(
        rotationDegrees = 0.0,
        fallbackReasons = (listOf("upstream_angle_not_accepted") + reasons).distinct().sorted(),
      )
    }
    throw IllegalStateException("Angle estimator returned an unsupported decision.")
  }

  private fun predictedDeskewSize(width: Int, height: Int, rotationDegrees: Double): Pair<Int, Int> {
    if (abs(rotationDegrees) < 1e-9) return width to height
    val radians = Math.toRadians(rotationDegrees)
    val cosine = abs(cos(radians))
    val sine = abs(sin(radians))
    return max(1, ceil(width * cosine + height * sine).toInt()) to
      max(1, ceil(width * sine + height * cosine).toInt())
  }

  private fun validateDeskewResourceBudget(
    sourceWidth: Int,
    sourceHeight: Int,
    outputWidth: Int,
    outputHeight: Int,
  ) {
    if (max(outputWidth, outputHeight) > MAX_DESKEW_OUTPUT_LONG_SIDE) {
      throw IllegalArgumentException("Full-frame deskew output exceeds the bounded dimension contract.")
    }
    val sourcePixels = sourceWidth.toLong() * sourceHeight
    val outputPixels = outputWidth.toLong() * outputHeight
    val accountedBytes = 4L * (sourcePixels + outputPixels)
    if (accountedBytes > MAX_DESKEW_ACCOUNTED_BYTES) {
      throw IllegalArgumentException("Full-frame deskew exceeds the bounded working-memory contract.")
    }
  }

  private fun rotateFullFrame(
    bitmap: Bitmap,
    rotationDegrees: Double,
    outputWidth: Int,
    outputHeight: Int,
  ): Bitmap {
    if (abs(rotationDegrees) < 1e-9) return bitmap
    val output = Bitmap.createBitmap(outputWidth, outputHeight, Bitmap.Config.ARGB_8888)
    output.eraseColor(Color.WHITE)
    val canvas = Canvas(output)
    canvas.translate(outputWidth / 2f, outputHeight / 2f)
    // The estimator returns the frozen Python/PIL sign convention; Android Canvas uses the opposite visual sign.
    canvas.rotate(-rotationDegrees.toFloat())
    canvas.translate(-bitmap.width / 2f, -bitmap.height / 2f)
    canvas.drawBitmap(
      bitmap,
      0f,
      0f,
      Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG),
    )
    bitmap.recycle()
    return output
  }

  private fun applyFullFrameDeskew(uriString: String, previewUri: String): Map<String, Any> {
    if (previewSourceUri != uriString) {
      throw IllegalArgumentException("Full-frame deskew source does not match the current geometry preview.")
    }
    val transformAngle = validatedTransformAngle(previewUri)
    val root = cacheRoot().canonicalFile
    if (!root.isDirectory) throw IllegalStateException("Geometry cache is unavailable.")
    val output = File(root, "deskewed.jpg")
    val transientSource = File(root, "source.img")
    output.delete()
    transientSource.delete()

    try {
      val source = materializeLocalImage(uriString, root)
      val (sourceWidth, sourceHeight) = readBounds(source)
      val orientation = readExifOrientation(source)
      var bitmap = decodeFullResolution(source)
      try {
        bitmap = orient(bitmap, orientation)
        val orientedWidth = bitmap.width
        val orientedHeight = bitmap.height
        val (outputWidth, outputHeight) = predictedDeskewSize(
          orientedWidth,
          orientedHeight,
          transformAngle.rotationDegrees,
        )
        validateDeskewResourceBudget(orientedWidth, orientedHeight, outputWidth, outputHeight)
        bitmap = rotateFullFrame(
          bitmap,
          transformAngle.rotationDegrees,
          outputWidth,
          outputHeight,
        )
        FileOutputStream(output).use { stream ->
          if (!bitmap.compress(Bitmap.CompressFormat.JPEG, DESKEW_JPEG_QUALITY, stream)) {
            throw IllegalStateException("Unable to encode the full-frame deskew output.")
          }
        }
        if (!output.isFile || output.length() <= 0L || output.length() > MAX_DESKEW_OUTPUT_BYTES) {
          throw IllegalStateException("Full-frame deskew output is missing, empty, or too large.")
        }
        return mapOf(
          "outputUri" to Uri.fromFile(output).toString(),
          "decision" to if (transformAngle.fallbackReasons.isEmpty()) "deskewed_full_frame" else "full_frame_fallback",
          "sourceWidth" to sourceWidth,
          "sourceHeight" to sourceHeight,
          "orientedWidth" to orientedWidth,
          "orientedHeight" to orientedHeight,
          "outputWidth" to outputWidth,
          "outputHeight" to outputHeight,
          "exifOrientation" to orientation,
          "rotationAppliedDegrees" to transformAngle.rotationDegrees,
          "fallbackReasons" to transformAngle.fallbackReasons,
        )
      } finally {
        if (!bitmap.isRecycled) bitmap.recycle()
      }
    } catch (error: Throwable) {
      output.delete()
      throw error
    } finally {
      transientSource.delete()
    }
  }

  private fun buildPreview(uriString: String): Map<String, Any> {
    val root = prepareCache()
    var copiedSource: File? = null
    var completed = false
    try {
      val source = materializeLocalImage(uriString, root)
      if (source.parentFile == root) copiedSource = source
      val (sourceWidth, sourceHeight) = readBounds(source)
      val orientation = readExifOrientation(source)
      val swapsAxes = orientation in listOf(
        ExifInterface.ORIENTATION_TRANSPOSE,
        ExifInterface.ORIENTATION_ROTATE_90,
        ExifInterface.ORIENTATION_TRANSVERSE,
        ExifInterface.ORIENTATION_ROTATE_270,
      )
      val orientedWidth = if (swapsAxes) sourceHeight else sourceWidth
      val orientedHeight = if (swapsAxes) sourceWidth else sourceHeight

      var bitmap = decodePreviewSource(source, sourceWidth, sourceHeight)
      bitmap = orient(bitmap, orientation)
      bitmap = scaleToPreview(bitmap, orientedWidth, orientedHeight)
      bitmap = grayscale(bitmap)
      val previewWidth = bitmap.width
      val previewHeight = bitmap.height
      val output = File(root, "preview.png")
      try {
        FileOutputStream(output).use { stream ->
          if (!bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)) {
            throw IllegalStateException("Unable to encode the geometry preview.")
          }
        }
      } finally {
        bitmap.recycle()
      }
      if (!output.isFile || output.length() <= 0L) {
        throw IllegalStateException("Geometry preview output is missing.")
      }

      previewSourceUri = uriString
      completed = true
      return mapOf(
        "previewUri" to Uri.fromFile(output).toString(),
        "sourceWidth" to sourceWidth,
        "sourceHeight" to sourceHeight,
        "orientedWidth" to orientedWidth,
        "orientedHeight" to orientedHeight,
        "previewWidth" to previewWidth,
        "previewHeight" to previewHeight,
        "exifOrientation" to orientation,
      )
    } finally {
      copiedSource?.delete()
      if (!completed) root.deleteRecursively()
    }
  }
}
