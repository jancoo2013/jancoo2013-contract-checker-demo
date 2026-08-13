package expo.modules.documentgeometrypreview

import android.graphics.Bitmap
import android.graphics.Color
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

private const val BOUNDARY_ANALYSIS_LONG_SIDE = 900
private const val MIN_CENTER_CORNER_CONTRAST = 20
private const val MIN_SUPPORTING_CORNERS = 2
private const val MIN_AXIS_OCCUPANCY = 0.20
private const val MIN_PAGE_AXIS_RATIO = 0.50
private const val MIN_REMOVABLE_AREA_RATIO = 0.05
private const val BOUNDARY_PADDING_RATIO = 0.02
private const val MAX_OUTSIDE_PAPER_RATIO = 0.0001
private const val MAX_OUTSIDE_SHADOW_RATIO = 0.005

internal object DocumentBoundaryEstimator {
  fun estimate(source: Bitmap, rotationDegrees: Double): List<Int>? {
    val analysis = scaledAnalysis(source)
    try {
      val width = analysis.width
      val height = analysis.height
      val pixels = IntArray(width * height)
      analysis.getPixels(pixels, 0, width, 0, 0, width, height)

      val center = medianLuma(
        pixels,
        width,
        (width * 0.30).roundToInt(),
        (height * 0.30).roundToInt(),
        (width * 0.70).roundToInt(),
        (height * 0.70).roundToInt(),
      )
      val cornerWidth = max(8, (width * 0.12).roundToInt())
      val cornerHeight = max(8, (height * 0.12).roundToInt())
      val corners = listOf(
        medianLuma(pixels, width, 0, 0, cornerWidth, cornerHeight),
        medianLuma(pixels, width, width - cornerWidth, 0, width, cornerHeight),
        medianLuma(pixels, width, 0, height - cornerHeight, cornerWidth, height),
        medianLuma(pixels, width, width - cornerWidth, height - cornerHeight, width, height),
      )
      val darkerCorners = corners.filter { center - it >= MIN_CENTER_CORNER_CONTRAST }
      val brighterCorners = corners.filter { it - center >= MIN_CENTER_CORNER_CONTRAST }
      val paperBrighter = when {
        darkerCorners.size >= MIN_SUPPORTING_CORNERS && darkerCorners.size > brighterCorners.size -> true
        brighterCorners.size >= MIN_SUPPORTING_CORNERS && brighterCorners.size > darkerCorners.size -> false
        else -> return null
      }
      val supporting = if (paperBrighter) darkerCorners else brighterCorners
      val background = median(supporting)
      val threshold = (center + background) / 2
      val rowCounts = IntArray(height)
      val columnCounts = IntArray(width)
      val onPaper = BooleanArray(width * height)
      val radians = Math.toRadians(rotationDegrees)
      val cosine = kotlin.math.cos(radians)
      val sine = kotlin.math.sin(radians)
      val pivotX = width / 2.0
      val pivotY = height / 2.0
      for (y in 0 until height) {
        val row = y * width
        for (x in 0 until width) {
          val sourceIndex = mappedSourceIndex(x, y, width, height, pivotX, pivotY, cosine, sine)
          if (sourceIndex < 0) continue
          val value = luma(pixels[sourceIndex])
          val classified = if (paperBrighter) value >= threshold else value <= threshold
          onPaper[row + x] = classified
          if (classified) {
            rowCounts[y] += 1
            columnCounts[x] += 1
          }
        }
      }

      val horizontal = activeRun(columnCounts, height, width / 2) ?: return null
      val vertical = activeRun(rowCounts, width, height / 2) ?: return null
      val ignoredCorners = BooleanArray(corners.size) { index ->
        val polarityOutlier = if (paperBrighter) center - corners[index] < MIN_CENTER_CORNER_CONTRAST
        else corners[index] - center < MIN_CENTER_CORNER_CONTRAST
        val localizedOutsideMainRuns = when (index) {
          0 -> horizontal.first >= cornerWidth / 2 && vertical.first >= cornerHeight / 2
          1 -> horizontal.second <= width - cornerWidth / 2 && vertical.first >= cornerHeight / 2
          2 -> horizontal.first >= cornerWidth / 2 && vertical.second <= height - cornerHeight / 2
          else -> horizontal.second <= width - cornerWidth / 2 &&
            vertical.second <= height - cornerHeight / 2
        }
        polarityOutlier && localizedOutsideMainRuns
      }
      var left = horizontal.first
      var right = horizontal.second
      var top = vertical.first
      var bottom = vertical.second

      if (
        (right - left).toDouble() / width < MIN_PAGE_AXIS_RATIO ||
        (bottom - top).toDouble() / height < MIN_PAGE_AXIS_RATIO
      ) return null

      val padX = max(4, (width * BOUNDARY_PADDING_RATIO).roundToInt())
      val padY = max(4, (height * BOUNDARY_PADDING_RATIO).roundToInt())
      left = max(0, left - padX)
      top = max(0, top - padY)
      right = min(width, right + padX)
      bottom = min(height, bottom + padY)

      if (
        hasUnsafeOutsideEvidence(
          pixels = pixels,
          onPaper = onPaper,
          width = width,
          height = height,
          left = left,
          top = top,
          right = right,
          bottom = bottom,
          paperBrighter = paperBrighter,
          center = center,
          background = background,
          threshold = threshold,
          ignoredCorners = ignoredCorners,
          cornerWidth = min(width, cornerWidth + padX),
          cornerHeight = min(height, cornerHeight + padY),
          pivotX = pivotX,
          pivotY = pivotY,
          cosine = cosine,
          sine = sine,
        )
      ) return null

      val analysisArea = width.toLong() * height
      val pageArea = (right - left).toLong() * (bottom - top)
      if (1.0 - pageArea.toDouble() / analysisArea < MIN_REMOVABLE_AREA_RATIO) return null

      val scaleX = source.width.toDouble() / width
      val scaleY = source.height.toDouble() / height
      val sourceLeft = floor(left * scaleX).toInt()
      val sourceTop = floor(top * scaleY).toInt()
      val sourceRight = ceil(right * scaleX).toInt()
      val sourceBottom = ceil(bottom * scaleY).toInt()

      val sourceArea = (sourceRight - sourceLeft).toLong() * (sourceBottom - sourceTop)
      if (1.0 - sourceArea.toDouble() / (source.width.toLong() * source.height) < MIN_REMOVABLE_AREA_RATIO) {
        return null
      }
      return listOf(sourceLeft, sourceTop, sourceRight, sourceBottom)
    } finally {
      if (analysis !== source && !analysis.isRecycled) analysis.recycle()
    }
  }

  private fun scaledAnalysis(source: Bitmap): Bitmap {
    val scale = min(1.0, BOUNDARY_ANALYSIS_LONG_SIDE.toDouble() / max(source.width, source.height))
    if (scale >= 1.0) return source
    return Bitmap.createScaledBitmap(
      source,
      max(1, (source.width * scale).roundToInt()),
      max(1, (source.height * scale).roundToInt()),
      true,
    )
  }

  private fun activeRun(counts: IntArray, denominator: Int, center: Int): Pair<Int, Int>? {
    val active = BooleanArray(counts.size) {
      counts[it].toDouble() / max(1, denominator) >= MIN_AXIS_OCCUPANCY
    }
    if (center !in active.indices || !active[center]) return null
    var left = center
    var right = center + 1
    while (left > 0 && active[left - 1]) left -= 1
    while (right < active.size && active[right]) right += 1
    return left to right
  }

  private fun hasUnsafeOutsideEvidence(
    pixels: IntArray,
    onPaper: BooleanArray,
    width: Int,
    height: Int,
    left: Int,
    top: Int,
    right: Int,
    bottom: Int,
    paperBrighter: Boolean,
    center: Int,
    background: Int,
    threshold: Int,
    ignoredCorners: BooleanArray,
    cornerWidth: Int,
    cornerHeight: Int,
    pivotX: Double,
    pivotY: Double,
    cosine: Double,
    sine: Double,
  ): Boolean {
    val area = width.toLong() * height
    val maxOutsidePaper = max(16, (area * MAX_OUTSIDE_PAPER_RATIO).roundToInt())
    val maxOutsideShadow = max(64, (area * MAX_OUTSIDE_SHADOW_RATIO).roundToInt())
    val backgroundTolerance = max(8, kotlin.math.abs(center - background) / 6)
    val thresholdDistance = kotlin.math.abs(threshold - background)
    var outsidePaper = 0
    var outsideShadow = 0

    for (y in 0 until height) {
      val row = y * width
      for (x in 0 until width) {
        if (x in left until right && y in top until bottom) continue
        if (isIgnoredCorner(x, y, width, height, ignoredCorners, cornerWidth, cornerHeight)) continue
        val sourceIndex = mappedSourceIndex(x, y, width, height, pivotX, pivotY, cosine, sine)
        if (sourceIndex < 0) continue
        if (onPaper[row + x]) {
          outsidePaper += 1
          if (outsidePaper > maxOutsidePaper) return true
          continue
        }
        val value = luma(pixels[sourceIndex])
        val towardPaper = if (paperBrighter) value - background else background - value
        if (towardPaper > backgroundTolerance && towardPaper < thresholdDistance) {
          outsideShadow += 1
          if (outsideShadow > maxOutsideShadow) return true
        }
      }
    }
    return false
  }

  private fun mappedSourceIndex(
    x: Int,
    y: Int,
    width: Int,
    height: Int,
    pivotX: Double,
    pivotY: Double,
    cosine: Double,
    sine: Double,
  ): Int {
    val dx = x - pivotX
    val dy = y - pivotY
    val sourceX = (pivotX + dx * cosine - dy * sine).roundToInt()
    val sourceY = (pivotY + dx * sine + dy * cosine).roundToInt()
    return if (sourceX in 0 until width && sourceY in 0 until height) sourceY * width + sourceX else -1
  }

  private fun isIgnoredCorner(
    x: Int,
    y: Int,
    width: Int,
    height: Int,
    ignoredCorners: BooleanArray,
    cornerWidth: Int,
    cornerHeight: Int,
  ): Boolean =
    (ignoredCorners[0] && x < cornerWidth && y < cornerHeight) ||
      (ignoredCorners[1] && x >= width - cornerWidth && y < cornerHeight) ||
      (ignoredCorners[2] && x < cornerWidth && y >= height - cornerHeight) ||
      (ignoredCorners[3] && x >= width - cornerWidth && y >= height - cornerHeight)

  private fun medianLuma(
    pixels: IntArray,
    width: Int,
    left: Int,
    top: Int,
    right: Int,
    bottom: Int,
  ): Int {
    val histogram = IntArray(256)
    var count = 0
    for (y in top until bottom) {
      val row = y * width
      for (x in left until right) {
        histogram[luma(pixels[row + x])] += 1
        count += 1
      }
    }
    var seen = 0
    val target = max(0, (count - 1) / 2)
    for (value in histogram.indices) {
      seen += histogram[value]
      if (seen > target) return value
    }
    return 0
  }

  private fun median(values: List<Int>): Int {
    val sorted = values.sorted()
    return sorted[sorted.size / 2]
  }

  private fun luma(pixel: Int): Int =
    (77 * Color.red(pixel) + 150 * Color.green(pixel) + 29 * Color.blue(pixel)) shr 8
}
