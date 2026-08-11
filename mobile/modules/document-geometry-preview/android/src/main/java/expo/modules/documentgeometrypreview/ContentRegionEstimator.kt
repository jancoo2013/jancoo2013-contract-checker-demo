package expo.modules.documentgeometrypreview

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.round
import kotlin.math.sin
import kotlin.math.sqrt

private const val MAX_MASK_LONG_SIDE = 1800
private const val MAX_ABS_DESKEW_DEGREES = 12.0
private const val MIN_LINE_COUNT = 4
private const val MIN_ANCHOR_WIDTH_RATIO = 0.18
private const val MIN_BAND_WIDTH_RATIO = 0.06
private const val MAX_BAND_HEIGHT_RATIO = 0.09
private const val MIN_CONTENT_WIDTH_RATIO = 0.20
private const val MIN_CONTENT_HEIGHT_RATIO = 0.12
private const val MIN_CONTENT_CONFIDENCE = 0.55
private const val MIN_EDGE_LOSS_PIXELS = 20
private const val MIN_EDGE_LOSS_AREA_RATIO = 0.00001

private data class ContentBox(
  val left: Int,
  val top: Int,
  val right: Int,
  val bottom: Int,
) {
  val width: Int get() = right - left
  fun asList(): List<Int> = listOf(left, top, right, bottom)
}

internal object ContentRegionEstimator {
  fun estimate(mask: Bitmap, deskewRotationDegrees: Double, angleDecision: String): Map<String, Any?> {
    validate(mask, deskewRotationDegrees, angleDecision)
    val width = mask.width
    val height = mask.height
    if (angleDecision != "accepted") {
      return result(
        width,
        height,
        deskewRotationDegrees,
        "full_frame_fallback",
        0.0,
        emptyList(),
        null,
        listOf("angle_not_accepted"),
      )
    }

    val (deskewed, sourceEdgeClipped) = deskewWithEdgeGuard(mask, deskewRotationDegrees)
    try {
      val bands = dominantBands(lineBands(deskewed), width)
      val reasons = mutableSetOf<String>()
      if (sourceEdgeClipped) reasons += "source_edge_content_clipped_by_deskew"
      if (bands.size < MIN_LINE_COUNT) reasons += "insufficient_line_bands"

      var candidate: ContentBox? = null
      var confidence = 0.0
      if (bands.isNotEmpty()) {
        val left = bands.minOf { it.left }
        val top = bands.minOf { it.top }
        val right = bands.maxOf { it.right }
        val bottom = bands.maxOf { it.bottom }
        candidate = ContentBox(left, top, right, bottom)
        val widthRatio = candidate.width.toDouble() / width
        val heightRatio = (candidate.bottom - candidate.top).toDouble() / height
        val edgeGuard = max(3, round(min(width, height) * 0.01).toInt())
        if (
          left <= edgeGuard || top <= edgeGuard ||
          right >= width - edgeGuard || bottom >= height - edgeGuard
        ) reasons += "content_touches_frame"
        if (widthRatio < MIN_CONTENT_WIDTH_RATIO || heightRatio < MIN_CONTENT_HEIGHT_RATIO) {
          reasons += "content_region_too_small"
        }

        val centers = bands.map { (it.left + it.right) / 2.0 }
        val mean = centers.average()
        val variance = centers.sumOf { (it - mean) * (it - mean) } / centers.size
        val spread = sqrt(variance) / max(1.0, width * 0.18)
        val alignment = max(0.0, 1.0 - min(1.0, spread))
        val lineFactor = min(1.0, bands.size / 8.0)
        val coverage = min(1.0, widthRatio / 0.55) * min(1.0, heightRatio / 0.55)
        confidence = min(1.0, 0.45 * lineFactor + 0.35 * alignment + 0.20 * coverage)
        if (confidence < MIN_CONTENT_CONFIDENCE) reasons += "low_confidence"
      }

      return result(
        width,
        height,
        deskewRotationDegrees,
        if (candidate != null && reasons.isEmpty()) "candidate_ready" else "rotation_only",
        rounded(confidence),
        bands,
        candidate,
        reasons.sorted(),
      )
    } finally {
      if (deskewed !== mask) deskewed.recycle()
    }
  }

  private fun validate(mask: Bitmap, rotation: Double, angleDecision: String) {
    if (mask.width <= 0 || mask.height <= 0 || max(mask.width, mask.height) > MAX_MASK_LONG_SIDE) {
      throw IllegalArgumentException("Content-region mask exceeds the bounded preview contract.")
    }
    if (angleDecision !in setOf("accepted", "rejected")) {
      throw IllegalArgumentException("Angle decision must be accepted or rejected.")
    }
    if (!rotation.isFinite() || abs(rotation) > MAX_ABS_DESKEW_DEGREES) {
      throw IllegalArgumentException("Deskew rotation exceeds the bounded content-region contract.")
    }
  }

  private fun deskewWithEdgeGuard(mask: Bitmap, rotation: Double): Pair<Bitmap, Boolean> {
    if (abs(rotation) < 1e-9) return mask to false
    val fixed = rotateMask(mask, rotation, expand = false)
    val expanded = rotateMask(mask, rotation, expand = true)
    val lost = max(0, countInk(expanded) - countInk(fixed))
    expanded.recycle()
    val minimumLoss = max(MIN_EDGE_LOSS_PIXELS, round(mask.width * mask.height * MIN_EDGE_LOSS_AREA_RATIO).toInt())
    return fixed to (lost >= minimumLoss)
  }

  private fun rotateMask(mask: Bitmap, rotation: Double, expand: Boolean): Bitmap {
    val radians = Math.toRadians(rotation)
    val outputWidth = if (expand) max(1, ceil(mask.width * abs(cos(radians)) + mask.height * abs(sin(radians))).toInt()) else mask.width
    val outputHeight = if (expand) max(1, ceil(mask.width * abs(sin(radians)) + mask.height * abs(cos(radians))).toInt()) else mask.height
    val output = Bitmap.createBitmap(outputWidth, outputHeight, Bitmap.Config.ARGB_8888)
    output.eraseColor(Color.WHITE)
    val canvas = Canvas(output)
    canvas.translate(outputWidth / 2f, outputHeight / 2f)
    canvas.rotate(-rotation.toFloat())
    canvas.translate(-mask.width / 2f, -mask.height / 2f)
    canvas.drawBitmap(mask, 0f, 0f, Paint().apply { isAntiAlias = false; isFilterBitmap = false })
    return output
  }

  private fun countInk(bitmap: Bitmap): Int {
    val pixels = IntArray(bitmap.width * bitmap.height)
    bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
    return pixels.count { (it and 0x00ffffff) == 0 }
  }

  private fun lineBands(mask: Bitmap): List<ContentBox> {
    val width = mask.width
    val height = mask.height
    val pixels = IntArray(width * height)
    mask.getPixels(pixels, 0, width, 0, 0, width, height)
    val rows = IntArray(height)
    for (y in 0 until height) {
      val start = y * width
      for (x in 0 until width) if ((pixels[start + x] and 0x00ffffff) == 0) rows[y] += 1
    }
    var window = max(3, round(height * 0.004).toInt())
    if (window % 2 == 0) window += 1
    val prefix = IntArray(height + 1)
    for (y in rows.indices) prefix[y + 1] = prefix[y] + rows[y]
    val half = window / 2
    val smoothed = DoubleArray(height) { y ->
      val top = max(0, y - half)
      val bottom = min(height, y + half + 1)
      (prefix[bottom] - prefix[top]).toDouble() / window
    }
    val positive = smoothed.filter { it > 0.0 }.sorted()
    val adaptive = if (positive.isEmpty()) 0.0 else percentile(positive, 0.55) * 0.30
    val threshold = max(3.0, max(width * 0.008, adaptive))
    val rowRuns = mergeRuns(runs(BooleanArray(height) { smoothed[it] >= threshold }), max(2, round(height * 0.003).toInt()))
    val bands = mutableListOf<ContentBox>()
    for ((rawTop, rawBottom) in rowRuns) {
      val top = max(0, rawTop - half)
      val bottom = min(height, rawBottom + half)
      val bandHeight = bottom - top
      if (bandHeight <= 1 || bandHeight > height * MAX_BAND_HEIGHT_RATIO) continue
      val columns = IntArray(width)
      for (y in top until bottom) {
        val start = y * width
        for (x in 0 until width) if ((pixels[start + x] and 0x00ffffff) == 0) columns[x] += 1
      }
      val columnThreshold = max(1, ceil(bandHeight * 0.15).toInt())
      val horizontalRuns = mergeRuns(runs(BooleanArray(width) { columns[it] >= columnThreshold }), max(3, round(width * 0.05).toInt()))
      if (horizontalRuns.isEmpty()) continue
      val best = horizontalRuns.maxWithOrNull(compareBy<Pair<Int, Int>> { it.second - it.first }.thenBy { run -> columns.sliceArray(run.first until run.second).sum() }) ?: continue
      if (best.second - best.first < width * MIN_BAND_WIDTH_RATIO) continue
      bands += ContentBox(best.first, top, best.second, bottom)
    }
    return bands
  }

  private fun dominantBands(bands: List<ContentBox>, width: Int): List<ContentBox> {
    val anchors = bands.filter { it.width >= width * MIN_ANCHOR_WIDTH_RATIO }
    if (anchors.isEmpty()) return emptyList()
    val coreLeft = round(median(anchors.map { it.left })).toInt()
    val coreRight = round(median(anchors.map { it.right })).toInt()
    val coreWidth = max(1, coreRight - coreLeft)
    val coreCenter = (coreLeft + coreRight) / 2.0
    return bands.filter { box ->
      val overlap = max(0, min(box.right, coreRight) - max(box.left, coreLeft)).toDouble()
      val overlapRatio = overlap / max(1, min(box.width, coreWidth))
      overlapRatio >= 0.30 || abs((box.left + box.right) / 2.0 - coreCenter) <= width * 0.12
    }.sortedWith(compareBy<ContentBox> { it.top }.thenBy { it.left })
  }

  private fun runs(active: BooleanArray): List<Pair<Int, Int>> {
    val result = mutableListOf<Pair<Int, Int>>()
    var start = -1
    for (index in active.indices) {
      if (active[index] && start < 0) start = index
      if (start >= 0 && (!active[index] || index == active.lastIndex)) {
        val end = if (active[index] && index == active.lastIndex) index + 1 else index
        result += start to end
        start = -1
      }
    }
    return result
  }

  private fun mergeRuns(runs: List<Pair<Int, Int>>, maxGap: Int): List<Pair<Int, Int>> {
    if (runs.isEmpty()) return emptyList()
    val merged = mutableListOf(runs.first())
    for ((start, end) in runs.drop(1)) {
      val previous = merged.last()
      if (start - previous.second <= maxGap) merged[merged.lastIndex] = previous.first to end else merged += start to end
    }
    return merged
  }

  private fun percentile(values: List<Double>, quantile: Double): Double {
    if (values.size == 1) return values.first()
    val position = (values.size - 1) * quantile
    val lower = position.toInt()
    val upper = ceil(position).toInt()
    return values[lower] + (values[upper] - values[lower]) * (position - lower)
  }

  private fun median(values: List<Int>): Double {
    val sorted = values.sorted()
    val middle = sorted.size / 2
    return if (sorted.size % 2 == 1) sorted[middle].toDouble() else (sorted[middle - 1] + sorted[middle]) / 2.0
  }

  private fun rounded(value: Double): Double = round(value * 10_000.0) / 10_000.0

  private fun result(
    width: Int,
    height: Int,
    rotation: Double,
    decision: String,
    confidence: Double,
    bands: List<ContentBox>,
    candidate: ContentBox?,
    reasons: List<String>,
  ): Map<String, Any?> = mapOf(
    "coordinateSpace" to if (decision == "full_frame_fallback") "source_preview" else "deskewed_preview",
    "previewWidth" to width,
    "previewHeight" to height,
    "deskewRotationDegrees" to rotation,
    "decision" to decision,
    "confidence" to confidence,
    "lineBands" to bands.map { it.asList() },
    "candidateContentBounds" to candidate?.asList(),
    "rejectionReasons" to reasons,
  )
}
