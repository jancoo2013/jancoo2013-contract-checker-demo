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

private const val MIN_OUTSIDE_BAND_WIDTH_RATIO = 0.025
private const val MIN_OUTSIDE_COMPACT_ROW_RATIO = 0.002
private const val MIN_OUTSIDE_COMPACT_PIXELS = 20
private const val MIN_OUTSIDE_COMPACT_AREA_RATIO = 0.00001
private const val MIN_OUTSIDE_VERTICAL_ARTIFACT_HEIGHT_RATIO = 0.08
private const val MAX_OUTSIDE_VERTICAL_ARTIFACT_ASPECT = 6.0

private data class CropBox(val left: Int, val top: Int, val right: Int, val bottom: Int) {
  fun asList(): List<Int> = listOf(left, top, right, bottom)
}

internal object SafeCropEstimator {
  fun authorize(
    mask: Bitmap,
    deskewRotationDegrees: Double,
    angleDecision: String,
    candidate: Map<String, Any?>,
  ): Map<String, Any?> {
    val decision = candidate["decision"] as? String
      ?: throw IllegalStateException("Content-region candidate decision is missing.")
    val coordinateSpace = candidate["coordinateSpace"] as? String
      ?: throw IllegalStateException("Content-region coordinate space is missing.")
    val candidateRotation = (candidate["deskewRotationDegrees"] as? Number)?.toDouble()
      ?: throw IllegalStateException("Content-region rotation is missing.")
    val width = (candidate["previewWidth"] as? Number)?.toInt()
      ?: throw IllegalStateException("Content-region preview width is missing.")
    val height = (candidate["previewHeight"] as? Number)?.toInt()
      ?: throw IllegalStateException("Content-region preview height is missing.")
    val reasons = ((candidate["rejectionReasons"] as? List<*>) ?: emptyList<Any>()).map {
      it as? String ?: throw IllegalStateException("Content-region rejection reason is invalid.")
    }.toMutableSet()

    if (angleDecision !in setOf("accepted", "rejected") || decision !in setOf("candidate_ready", "rotation_only", "full_frame_fallback")) {
      throw IllegalStateException("Content-region decision contract is invalid.")
    }
    if (!deskewRotationDegrees.isFinite() || !candidateRotation.isFinite() || abs(candidateRotation - deskewRotationDegrees) > 1e-6) {
      throw IllegalStateException("Content-region rotation disagrees with angle evidence.")
    }
    if (width != mask.width || height != mask.height) {
      throw IllegalStateException("Content-region candidate dimensions disagree with the mask.")
    }
    if (angleDecision == "rejected" && (decision != "full_frame_fallback" || coordinateSpace != "source_preview")) {
      throw IllegalStateException("Rejected angle requires source-preview full-frame fallback.")
    }
    if (angleDecision == "accepted" && (decision == "full_frame_fallback" || coordinateSpace != "deskewed_preview")) {
      throw IllegalStateException("Accepted angle requires deskewed-preview candidate evidence.")
    }
    if (angleDecision != "accepted" || decision != "candidate_ready") {
      return candidate + mapOf("safeCropBounds" to null)
    }

    val fixed = rotateMask(mask, deskewRotationDegrees, expand = false)
    val expanded = rotateMask(mask, deskewRotationDegrees, expand = true)
    try {
      if (expanded !== fixed) {
        val meaningfulLoss = max(
          MIN_OUTSIDE_COMPACT_PIXELS,
          round(mask.width.toLong() * mask.height * MIN_OUTSIDE_COMPACT_AREA_RATIO).toInt(),
        )
        if (countBlack(expanded) - countBlack(fixed) >= meaningfulLoss) {
          reasons += "source_edge_content_clipped_by_deskew"
        }
      }

      val box = parseBox(candidate["candidateContentBounds"], width, height)
        ?: throw IllegalStateException("Crop-ready candidate is missing content bounds.")
      val padX = max(12, round(width * 0.04).toInt())
      val padY = max(12, round(height * 0.04).toInt())
      val padded = CropBox(
        max(0, box.left - padX),
        max(0, box.top - padY),
        min(width, box.right + padX),
        min(height, box.bottom + padY),
      )
      if (
        (padded.right - padded.left).toDouble() / width >= 0.985 ||
        (padded.bottom - padded.top).toDouble() / height >= 0.985
      ) reasons += "content_region_nearly_full_frame"
      if (hasDisconnectedContentOutside(fixed, padded)) {
        reasons += "disconnected_content_outside_crop"
      }

      return candidate + mapOf(
        "decision" to if (reasons.isEmpty()) "accepted" else "rotation_only",
        "safeCropBounds" to if (reasons.isEmpty()) padded.asList() else null,
        "rejectionReasons" to reasons.sorted(),
      )
    } finally {
      if (expanded !== mask && expanded !== fixed) expanded.recycle()
      if (fixed !== mask) fixed.recycle()
    }
  }

  private fun parseBox(value: Any?, width: Int, height: Int): CropBox? {
    if (value == null) return null
    val values = (value as? List<*>)?.map { (it as? Number)?.toInt() }
      ?: throw IllegalStateException("Content bounds are invalid.")
    if (values.size != 4 || values.any { it == null }) throw IllegalStateException("Content bounds are invalid.")
    val (left, top, right, bottom) = values.map { it!! }
    if (!(0 <= left && left < right && right <= width && 0 <= top && top < bottom && bottom <= height)) {
      throw IllegalStateException("Content bounds exceed the preview.")
    }
    return CropBox(left, top, right, bottom)
  }

  private fun rotateMask(mask: Bitmap, rotation: Double, expand: Boolean): Bitmap {
    if (abs(rotation) < 1e-9) return mask
    val radians = Math.toRadians(rotation)
    val outputWidth = if (expand) ceil(mask.width * abs(cos(radians)) + mask.height * abs(sin(radians))).toInt() else mask.width
    val outputHeight = if (expand) ceil(mask.width * abs(sin(radians)) + mask.height * abs(cos(radians))).toInt() else mask.height
    val output = Bitmap.createBitmap(max(1, outputWidth), max(1, outputHeight), Bitmap.Config.ARGB_8888)
    output.eraseColor(Color.WHITE)
    val canvas = Canvas(output)
    canvas.translate(output.width / 2f, output.height / 2f)
    canvas.rotate(-rotation.toFloat())
    canvas.translate(-mask.width / 2f, -mask.height / 2f)
    canvas.drawBitmap(mask, 0f, 0f, Paint().apply { isAntiAlias = false; isFilterBitmap = false })
    return output
  }

  private fun countBlack(bitmap: Bitmap): Int {
    val row = IntArray(bitmap.width)
    var total = 0
    for (y in 0 until bitmap.height) {
      bitmap.getPixels(row, 0, bitmap.width, 0, y, bitmap.width, 1)
      total += row.count { (it and 0x00ffffff) == 0 }
    }
    return total
  }

  private fun hasDisconnectedContentOutside(mask: Bitmap, crop: CropBox): Boolean {
    val outside = mask.copy(Bitmap.Config.ARGB_8888, true)
      ?: throw IllegalStateException("Unable to allocate bounded crop-safety mask.")
    try {
      Canvas(outside).drawRect(
        crop.left.toFloat(), crop.top.toFloat(), crop.right.toFloat(), crop.bottom.toFloat(),
        Paint().apply { color = Color.WHITE; style = Paint.Style.FILL },
      )
      val width = outside.width
      val height = outside.height
      val pixels = IntArray(width * height)
      outside.getPixels(pixels, 0, width, 0, 0, width, height)
      return hasOutsideLine(pixels, width, height) || hasCompactForeground(pixels, width, height)
    } finally {
      outside.recycle()
    }
  }

  private fun hasOutsideLine(pixels: IntArray, width: Int, height: Int): Boolean {
    val rows = IntArray(height)
    for (y in 0 until height) for (x in 0 until width) {
      if ((pixels[y * width + x] and 0x00ffffff) == 0) rows[y]++
    }
    var window = max(3, round(height * 0.004).toInt())
    if (window % 2 == 0) window++
    val prefix = IntArray(height + 1)
    for (y in 0 until height) prefix[y + 1] = prefix[y] + rows[y]
    val half = window / 2
    val smoothed = DoubleArray(height) { y ->
      val top = max(0, y - half)
      val bottom = min(height, y + half + 1)
      (prefix[bottom] - prefix[top]).toDouble() / window
    }
    val positive = smoothed.filter { it > 0.0 }.sorted()
    val adaptive = if (positive.isEmpty()) 0.0 else percentile(positive, 0.55) * 0.30
    val threshold = max(3.0, max(width * 0.008, adaptive))
    val active = BooleanArray(height) { smoothed[it] >= threshold }
    for ((rawTop, rawBottom) in mergeRuns(runs(active), max(2, round(height * 0.003).toInt()))) {
      val top = max(0, rawTop - half)
      val bottom = min(height, rawBottom + half)
      val bandHeight = bottom - top
      if (bandHeight <= 1 || bandHeight > height * 0.09) continue
      val columns = IntArray(width)
      for (y in top until bottom) for (x in 0 until width) {
        if ((pixels[y * width + x] and 0x00ffffff) == 0) columns[x]++
      }
      val colThreshold = max(1, ceil(bandHeight * 0.15).toInt())
      val horizontal = mergeRuns(runs(BooleanArray(width) { columns[it] >= colThreshold }), max(3, round(width * 0.05).toInt()))
      if (horizontal.any { it.second - it.first >= width * MIN_OUTSIDE_BAND_WIDTH_RATIO }) return true
    }
    return false
  }

  private fun hasCompactForeground(pixels: IntArray, width: Int, height: Int): Boolean {
    val rowCounts = IntArray(height)
    for (y in 0 until height) for (x in 0 until width) {
      if ((pixels[y * width + x] and 0x00ffffff) == 0) rowCounts[y]++
    }
    val rowThreshold = max(2, ceil(width * MIN_OUTSIDE_COMPACT_ROW_RATIO).toInt())
    val minPixels = max(MIN_OUTSIDE_COMPACT_PIXELS, round(width.toLong() * height * MIN_OUTSIDE_COMPACT_AREA_RATIO).toInt())
    for ((top, bottom) in mergeRuns(runs(BooleanArray(height) { rowCounts[it] >= rowThreshold }), max(1, round(height * 0.002).toInt()))) {
      var count = 0
      var left = width
      var right = -1
      var actualTop = height
      var actualBottom = -1
      for (y in top until bottom) for (x in 0 until width) {
        if ((pixels[y * width + x] and 0x00ffffff) == 0) {
          count++; left = min(left, x); right = max(right, x); actualTop = min(actualTop, y); actualBottom = max(actualBottom, y)
        }
      }
      if (count < minPixels || right < left) continue
      val bandWidth = right - left + 1
      val bandHeight = actualBottom - actualTop + 1
      val longVertical = bandHeight > bandWidth * MAX_OUTSIDE_VERTICAL_ARTIFACT_ASPECT &&
        bandHeight >= height * MIN_OUTSIDE_VERTICAL_ARTIFACT_HEIGHT_RATIO
      if (!longVertical) return true
    }
    return false
  }

  private fun percentile(values: List<Double>, quantile: Double): Double {
    if (values.size == 1) return values.first()
    val position = (values.size - 1) * quantile
    val lower = position.toInt()
    val upper = ceil(position).toInt()
    return values[lower] + (values[upper] - values[lower]) * (position - lower)
  }

  private fun runs(active: BooleanArray): List<Pair<Int, Int>> {
    val result = mutableListOf<Pair<Int, Int>>()
    var start = -1
    for (index in active.indices) {
      if (active[index] && start < 0) start = index
      if (start >= 0 && (!active[index] || index == active.lastIndex)) {
        result += start to if (active[index] && index == active.lastIndex) index + 1 else index
        start = -1
      }
    }
    return result
  }

  private fun mergeRuns(items: List<Pair<Int, Int>>, maxGap: Int): List<Pair<Int, Int>> {
    if (items.isEmpty()) return emptyList()
    val merged = mutableListOf(items.first())
    for ((start, end) in items.drop(1)) {
      val previous = merged.last()
      if (start - previous.second <= maxGap) merged[merged.lastIndex] = previous.first to end else merged += start to end
    }
    return merged
  }
}
