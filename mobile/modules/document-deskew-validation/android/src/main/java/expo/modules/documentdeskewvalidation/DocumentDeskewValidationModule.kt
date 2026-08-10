package expo.modules.documentdeskewvalidation

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.media.ExifInterface
import android.net.Uri
import android.os.SystemClock
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.functions.Coroutine
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File
import java.io.FileOutputStream
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.round
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

private const val PREVIEW_LONG_SIDE = 1800
private const val ANALYSIS_LONG_SIDE = 900
private const val MAX_SOURCE_LONG_SIDE = 8192
private const val MAX_SOURCE_PIXELS = 16_000_000L
private const val MAX_SOURCE_BYTES = 64L * 1024L * 1024L
private const val MAX_ANGLE = 12
private const val MIN_FOREGROUND_RATIO = 0.0005
private const val MAX_FOREGROUND_RATIO = 0.22
private const val MIN_CONFIDENCE = 0.45
private const val MIN_PROJECTION_GAIN = 0.18
private const val MIN_PEAK_MARGIN = 0.04
private const val MIN_EDGE_LOSS_PIXELS = 20
private const val MIN_EDGE_LOSS_RATIO = 0.00001

private data class MaskResult(
  val mask: BooleanArray,
  val width: Int,
  val height: Int,
  val threshold: Double,
  val foregroundRatio: Double
)

private data class AngleResult(
  val deskew: Double,
  val dominant: Double,
  val confidence: Double,
  val decision: String,
  val reasons: List<String>
)

class DocumentDeskewValidationModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  override fun definition() = ModuleDefinition {
    Name("DocumentDeskewValidation")
    AsyncFunction("normalizeAsync") Coroutine { uriString: String -> normalize(uriString) }
  }

  private fun localFile(uriString: String): File {
    val uri = Uri.parse(uriString)
    if (uri.scheme != null && uri.scheme != "file") {
      throw IllegalArgumentException("Only a local file URI is supported by this validation harness.")
    }
    val file = File(uri.path ?: uriString)
    if (!file.isFile || file.length() <= 0L || file.length() > MAX_SOURCE_BYTES) {
      throw IllegalArgumentException("Selected image is missing, empty, or too large for local validation.")
    }
    return file
  }

  private fun decodeOriented(file: File): Bitmap {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
      throw IllegalArgumentException("Selected file is not a readable bitmap image.")
    }
    if (max(bounds.outWidth, bounds.outHeight) > MAX_SOURCE_LONG_SIDE ||
      bounds.outWidth.toLong() * bounds.outHeight.toLong() > MAX_SOURCE_PIXELS
    ) {
      throw IllegalArgumentException("Selected image exceeds the bounded Android validation size.")
    }
    val decoded = BitmapFactory.decodeFile(
      file.absolutePath,
      BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888 }
    ) ?: throw IllegalArgumentException("Unable to decode the selected image.")

    val orientation = runCatching {
      ExifInterface(file.absolutePath).getAttributeInt(
        ExifInterface.TAG_ORIENTATION,
        ExifInterface.ORIENTATION_NORMAL
      )
    }.getOrDefault(ExifInterface.ORIENTATION_NORMAL)
    val matrix = Matrix()
    when (orientation) {
      ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.setScale(-1f, 1f)
      ExifInterface.ORIENTATION_ROTATE_180 -> matrix.setRotate(180f)
      ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.setScale(1f, -1f)
      ExifInterface.ORIENTATION_TRANSPOSE -> { matrix.setRotate(90f); matrix.postScale(-1f, 1f) }
      ExifInterface.ORIENTATION_ROTATE_90 -> matrix.setRotate(90f)
      ExifInterface.ORIENTATION_TRANSVERSE -> { matrix.setRotate(-90f); matrix.postScale(-1f, 1f) }
      ExifInterface.ORIENTATION_ROTATE_270 -> matrix.setRotate(-90f)
      else -> return decoded
    }
    val oriented = Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
    if (oriented !== decoded) decoded.recycle()
    return oriented
  }

  private fun boxBlur(source: IntArray, width: Int, height: Int, radius: Int): IntArray {
    val temp = IntArray(source.size)
    val output = IntArray(source.size)
    for (y in 0 until height) {
      var sum = 0
      var left = 0
      var right = -1
      for (x in 0 until width) {
        val wantedLeft = max(0, x - radius)
        val wantedRight = min(width - 1, x + radius)
        while (right < wantedRight) { right += 1; sum += source[y * width + right] }
        while (left < wantedLeft) { sum -= source[y * width + left]; left += 1 }
        temp[y * width + x] = sum / (right - left + 1)
      }
    }
    for (x in 0 until width) {
      var sum = 0
      var top = 0
      var bottom = -1
      for (y in 0 until height) {
        val wantedTop = max(0, y - radius)
        val wantedBottom = min(height - 1, y + radius)
        while (bottom < wantedBottom) { bottom += 1; sum += temp[bottom * width + x] }
        while (top < wantedTop) { sum -= temp[top * width + x]; top += 1 }
        output[y * width + x] = sum / (bottom - top + 1)
      }
    }
    return output
  }

  private fun histogramValueAtRank(histogram: IntArray, rank: Int): Int {
    var seen = 0
    for (value in histogram.indices) {
      seen += histogram[value]
      if (seen > rank) return value
    }
    return histogram.lastIndex
  }

  private fun quantile(histogram: IntArray, total: Int, q: Double): Double {
    val position = (total - 1) * q
    val lowRank = floor(position).toInt()
    val highRank = ceil(position).toInt()
    val low = histogramValueAtRank(histogram, lowRank)
    val high = histogramValueAtRank(histogram, highRank)
    return low + (position - lowRank) * (high - low)
  }

  private fun buildMask(source: Bitmap): MaskResult {
    val scale = min(1.0, PREVIEW_LONG_SIDE.toDouble() / max(source.width, source.height))
    val width = max(1, round(source.width * scale).toInt())
    val height = max(1, round(source.height * scale).toInt())
    val preview = if (width == source.width && height == source.height) source
      else Bitmap.createScaledBitmap(source, width, height, true)
    val pixels = IntArray(width * height)
    preview.getPixels(pixels, 0, width, 0, 0, width, height)
    if (preview !== source) preview.recycle()

    val gray = IntArray(pixels.size)
    for (index in pixels.indices) {
      val color = pixels[index]
      gray[index] = (77 * Color.red(color) + 150 * Color.green(color) + 29 * Color.blue(color) + 128) shr 8
    }
    val gaussianRadius = max(5.0, min(width, height) * 0.012)
    val boxRadius = max(2, round(gaussianRadius / sqrt(3.0)).toInt())
    var background = gray
    repeat(3) { background = boxBlur(background, width, height, boxRadius) }

    val contrast = IntArray(gray.size)
    val histogram = IntArray(256)
    for (index in gray.indices) {
      val value = (background[index] - gray[index]).coerceIn(0, 255)
      contrast[index] = value
      histogram[value] += 1
    }
    val median = quantile(histogram, contrast.size, 0.5)
    val deviationHistogram = IntArray(256)
    for (value in contrast) deviationHistogram[abs(value - median).roundToInt().coerceIn(0, 255)] += 1
    val mad = quantile(deviationHistogram, contrast.size, 0.5)
    val p92 = quantile(histogram, contrast.size, 0.92)
    val threshold = min(48.0, max(9.0, max(median + 4.0 * max(mad, 1.0), p92 * 0.42)))
    val mask = BooleanArray(contrast.size)
    var foreground = 0
    for (index in contrast.indices) if (contrast[index] >= threshold) { mask[index] = true; foreground += 1 }
    return MaskResult(mask, width, height, threshold, foreground.toDouble() / mask.size)
  }

  private fun analysisMask(mask: MaskResult): MaskResult {
    val scale = min(1.0, ANALYSIS_LONG_SIDE.toDouble() / max(mask.width, mask.height))
    if (scale == 1.0) return mask
    val width = max(1, round(mask.width * scale).toInt())
    val height = max(1, round(mask.height * scale).toInt())
    val resized = BooleanArray(width * height)
    for (y in 0 until height) for (x in 0 until width) {
      val sx = min(mask.width - 1, floor(x.toDouble() * mask.width / width).toInt())
      val sy = min(mask.height - 1, floor(y.toDouble() * mask.height / height).toInt())
      resized[y * width + x] = mask.mask[sy * mask.width + sx]
    }
    return MaskResult(resized, width, height, mask.threshold, mask.foregroundRatio)
  }

  private fun rotationStats(mask: BooleanArray, width: Int, height: Int, pillowAngle: Double, outWidth: Int, outHeight: Int): Pair<Long, Long> {
    val radians = Math.toRadians(-pillowAngle)
    val c = cos(radians)
    val s = sin(radians)
    val sourceCx = (width - 1) / 2.0
    val sourceCy = (height - 1) / 2.0
    val outCx = (outWidth - 1) / 2.0
    val outCy = (outHeight - 1) / 2.0
    var total = 0L
    var squaredRows = 0L
    for (y in 0 until outHeight) {
      var row = 0L
      val dy = y - outCy
      for (x in 0 until outWidth) {
        val dx = x - outCx
        val sx = (c * dx + s * dy + sourceCx).roundToInt()
        val sy = (-s * dx + c * dy + sourceCy).roundToInt()
        if (sx in 0 until width && sy in 0 until height && mask[sy * width + sx]) row += 1
      }
      total += row
      squaredRows += row * row
    }
    return total to squaredRows
  }

  private fun projectionScore(mask: MaskResult, angle: Double): Double {
    val (total, squares) = rotationStats(mask.mask, mask.width, mask.height, angle, mask.width, mask.height)
    if (total <= 0L) return 0.0
    return squares.toDouble() / (total.toDouble() * total.toDouble()) * mask.height
  }

  private fun estimateAngle(mask: MaskResult): AngleResult {
    val reasons = mutableSetOf<String>()
    if (mask.foregroundRatio < MIN_FOREGROUND_RATIO) reasons += "insufficient_foreground"
    if (mask.foregroundRatio > MAX_FOREGROUND_RATIO) reasons += "excessive_foreground"
    val bounded = analysisMask(mask)
    val scored = (-MAX_ANGLE..MAX_ANGLE).map { it.toDouble() to projectionScore(bounded, it.toDouble()) }
    val best = scored.maxWith(compareBy<Pair<Double, Double>> { it.second }.thenBy { -abs(it.first) })
    val sortedScores = scored.map { it.second }.sorted()
    val medianScore = sortedScores[sortedScores.size / 2]
    val gain = if (best.second <= 0.0) 0.0 else max(0.0, (best.second - medianScore) / best.second)
    val second = scored.filter { abs(it.first - best.first) > 1.0 }.maxOfOrNull { it.second } ?: 0.0
    val margin = if (best.second <= 0.0) 0.0 else max(0.0, (best.second - second) / best.second)
    val confidence = min(1.0, 1.15 * gain + 0.75 * margin)
    if (gain < MIN_PROJECTION_GAIN) reasons += "unstable_projection"
    if (margin < MIN_PEAK_MARGIN) reasons += "ambiguous_angle_peak"
    if (abs(best.first) == MAX_ANGLE.toDouble()) reasons += "angle_at_search_limit"
    if (confidence < MIN_CONFIDENCE) reasons += "low_confidence"
    return AngleResult(best.first, -best.first, confidence, if (reasons.isEmpty()) "accepted" else "rejected", reasons.sorted())
  }

  private fun clipsMeaningfulEdge(mask: MaskResult, angle: Double): Boolean {
    if (abs(angle) < 1e-9) return false
    val bounded = rotationStats(mask.mask, mask.width, mask.height, angle, mask.width, mask.height).first
    val radians = Math.toRadians(angle)
    val expandedWidth = ceil(abs(mask.width * cos(radians)) + abs(mask.height * sin(radians))).toInt()
    val expandedHeight = ceil(abs(mask.height * cos(radians)) + abs(mask.width * sin(radians))).toInt()
    val expanded = rotationStats(mask.mask, mask.width, mask.height, angle, expandedWidth, expandedHeight).first
    val lost = max(0L, expanded - bounded)
    val minimum = max(MIN_EDGE_LOSS_PIXELS.toLong(), round(mask.mask.size * MIN_EDGE_LOSS_RATIO).toLong())
    return lost >= minimum
  }

  private fun rotateFullFrame(source: Bitmap, pillowAngle: Double): Bitmap {
    val output = Bitmap.createBitmap(source.width, source.height, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(output)
    canvas.drawColor(Color.WHITE)
    canvas.rotate((-pillowAngle).toFloat(), source.width / 2f, source.height / 2f)
    canvas.drawBitmap(source, 0f, 0f, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
    return output
  }

  private fun saveOutput(bitmap: Bitmap): String {
    val directory = File(context.cacheDir, "deskew-validation").apply { mkdirs() }
    directory.listFiles()?.forEach { it.delete() }
    val file = File(directory, "deskew-${System.currentTimeMillis()}.jpg")
    FileOutputStream(file).use { output ->
      if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 95, output)) {
        throw IllegalStateException("Unable to save the local deskew validation result.")
      }
    }
    return Uri.fromFile(file).toString()
  }

  private fun normalize(uriString: String): Map<String, Any> {
    val startedAt = SystemClock.elapsedRealtime()
    val source = decodeOriented(localFile(uriString))
    try {
      val mask = buildMask(source)
      val angle = estimateAngle(mask)
      val edgeClipped = angle.decision == "accepted" && clipsMeaningfulEdge(mask, angle.deskew)
      val reasons = angle.reasons.toMutableList()
      if (edgeClipped) reasons += "source_edge_content_clipped_by_deskew"
      val applyRotation = angle.decision == "accepted" && !edgeClipped && abs(angle.deskew) >= 1e-9
      val outputUri = if (applyRotation) {
        val rotated = rotateFullFrame(source, angle.deskew)
        try { saveOutput(rotated) } finally { rotated.recycle() }
      } else uriString
      return mapOf(
        "decision" to if (applyRotation) "deskewed_full_frame" else "full_frame_fallback",
        "outputUri" to outputUri,
        "sourceWidth" to source.width,
        "sourceHeight" to source.height,
        "previewWidth" to mask.width,
        "previewHeight" to mask.height,
        "dominantTextAngleDegrees" to round(angle.dominant * 100.0) / 100.0,
        "deskewRotationDegrees" to round(angle.deskew * 100.0) / 100.0,
        "rotationAppliedDegrees" to if (applyRotation) round(angle.deskew * 100.0) / 100.0 else 0.0,
        "confidence" to round(angle.confidence * 10_000.0) / 10_000.0,
        "foregroundRatio" to round(mask.foregroundRatio * 100_000_000.0) / 100_000_000.0,
        "threshold" to round(mask.threshold * 100.0) / 100.0,
        "angleDecision" to angle.decision,
        "rejectionReasons" to reasons.sorted(),
        "elapsedMs" to (SystemClock.elapsedRealtime() - startedAt)
      )
    } finally {
      source.recycle()
    }
  }
}
