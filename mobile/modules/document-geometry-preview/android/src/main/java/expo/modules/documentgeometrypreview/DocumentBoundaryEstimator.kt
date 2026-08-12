package expo.modules.documentgeometrypreview

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Matrix
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

private const val BOUNDARY_ANALYSIS_LONG_SIDE = 900
private const val MIN_CENTER_CORNER_CONTRAST = 20
private const val MIN_SUPPORTING_CORNERS = 2
private const val MIN_AXIS_OCCUPANCY = 0.30
private const val MIN_PAGE_AXIS_RATIO = 0.50
private const val MIN_REMOVABLE_AREA_RATIO = 0.05
private const val BOUNDARY_PADDING_RATIO = 0.015

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
        darkerCorners.size >= MIN_SUPPORTING_CORNERS && darkerCorners.size >= brighterCorners.size -> true
        brighterCorners.size >= MIN_SUPPORTING_CORNERS -> false
        else -> return null
      }
      val supporting = if (paperBrighter) darkerCorners else brighterCorners
      val background = median(supporting)
      val threshold = (center + background) / 2

      val rowCounts = IntArray(height)
      val columnCounts = IntArray(width)
      for (y in 0 until height) {
        val row = y * width
        for (x in 0 until width) {
          val value = luma(pixels[row + x])
          val onPaper = if (paperBrighter) value >= threshold else value <= threshold
          if (onPaper) {
            rowCounts[y] += 1
            columnCounts[x] += 1
          }
        }
      }

      val horizontal = activeRun(columnCounts, height, width / 2) ?: return null
      val vertical = activeRun(rowCounts, width, height / 2) ?: return null
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

      val analysisArea = width.toLong() * height
      val pageArea = (right - left).toLong() * (bottom - top)
      if (1.0 - pageArea.toDouble() / analysisArea < MIN_REMOVABLE_AREA_RATIO) return null

      val scaleX = source.width.toDouble() / width
      val scaleY = source.height.toDouble() / height
      val sourceLeft = floor(left * scaleX).toInt()
      val sourceTop = floor(top * scaleY).toInt()
      val sourceRight = ceil(right * scaleX).toInt()
      val sourceBottom = ceil(bottom * scaleY).toInt()

      val points = floatArrayOf(
        sourceLeft.toFloat(), sourceTop.toFloat(),
        sourceRight.toFloat(), sourceTop.toFloat(),
        sourceRight.toFloat(), sourceBottom.toFloat(),
        sourceLeft.toFloat(), sourceBottom.toFloat(),
      )
      Matrix().apply {
        setRotate(-rotationDegrees.toFloat(), source.width / 2f, source.height / 2f)
        mapPoints(points)
      }
      val mappedLeft = floor(minOf(points[0], points[2], points[4], points[6]).toDouble()).toInt()
      val mappedTop = floor(minOf(points[1], points[3], points[5], points[7]).toDouble()).toInt()
      val mappedRight = ceil(maxOf(points[0], points[2], points[4], points[6]).toDouble()).toInt()
      val mappedBottom = ceil(maxOf(points[1], points[3], points[5], points[7]).toDouble()).toInt()
      if (
        mappedLeft < 0 || mappedTop < 0 || mappedRight > source.width || mappedBottom > source.height ||
        mappedLeft >= mappedRight || mappedTop >= mappedBottom
      ) return null

      val mappedArea = (mappedRight - mappedLeft).toLong() * (mappedBottom - mappedTop)
      if (1.0 - mappedArea.toDouble() / (source.width.toLong() * source.height) < MIN_REMOVABLE_AREA_RATIO) {
        return null
      }
      return listOf(mappedLeft, mappedTop, mappedRight, mappedBottom)
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
