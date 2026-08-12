package expo.modules.documentgeometrypreview

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

private const val PREPARED_PREVIEW_LONG_SIDE = 1800
private const val PREPARED_MAX_ABS_ROTATION = 12.0
private const val PREPARED_MAX_OUTPUT_LONG_SIDE = 10_000
private const val PREPARED_MAX_ACCOUNTED_BYTES = 384L * 1024L * 1024L

internal data class PreparedDocumentPixels(
  val bitmap: Bitmap,
  val decision: String,
  val rotationAppliedDegrees: Double,
  val cropBoxSource: List<Int>?,
  val fallbackReasons: List<String>,
)

private data class PreparedCropBox(
  val left: Int,
  val top: Int,
  val right: Int,
  val bottom: Int,
) {
  val width: Int get() = right - left
  val height: Int get() = bottom - top
  fun asList(): List<Int> = listOf(left, top, right, bottom)
}

internal object PreparedDocumentTransform {
  fun apply(source: Bitmap, region: Map<String, Any?>): PreparedDocumentPixels {
    val decision = region["decision"] as? String
      ?: throw IllegalStateException("Content-region decision is missing.")
    val coordinateSpace = region["coordinateSpace"] as? String
      ?: throw IllegalStateException("Content-region coordinate space is missing.")
    val rotation = (region["deskewRotationDegrees"] as? Number)?.toDouble()
      ?: throw IllegalStateException("Content-region rotation is missing.")
    val previewWidth = (region["previewWidth"] as? Number)?.toInt()
      ?: throw IllegalStateException("Content-region preview width is missing.")
    val previewHeight = (region["previewHeight"] as? Number)?.toInt()
      ?: throw IllegalStateException("Content-region preview height is missing.")
    val reasons = ((region["rejectionReasons"] as? List<*>) ?: emptyList<Any>()).map {
      it as? String ?: throw IllegalStateException("Content-region rejection reason is invalid.")
    }

    if (decision !in setOf("accepted", "rotation_only", "full_frame_fallback")) {
      throw IllegalStateException("Unsupported content-region decision.")
    }
    if (!rotation.isFinite() || abs(rotation) > PREPARED_MAX_ABS_ROTATION) {
      throw IllegalStateException("Content-region rotation violates the prepared-image contract.")
    }
    val expectedPreview = expectedPreviewSize(source.width, source.height)
    if (previewWidth != expectedPreview.first || previewHeight != expectedPreview.second) {
      throw IllegalStateException("Content-region preview dimensions disagree with the oriented source.")
    }

    if (decision != "accepted") {
      if (region["safeCropBounds"] != null) {
        throw IllegalStateException("Non-accepted content region cannot authorize a crop.")
      }
      if (
        (decision == "full_frame_fallback" && coordinateSpace != "source_preview") ||
        (decision == "rotation_only" && coordinateSpace != "deskewed_preview")
      ) {
        throw IllegalStateException("Content-region fallback coordinate space is contradictory.")
      }

      if (decision == "rotation_only") {
        val (outputWidth, outputHeight) = predictedExpandedSize(source.width, source.height, rotation)
        validateFullFrameBudget(source.width, source.height, outputWidth, outputHeight)
        return PreparedDocumentPixels(
          bitmap = renderGrayscaleExpandedFrame(source, rotation, outputWidth, outputHeight),
          decision = "deskewed_full_frame_grayscale",
          rotationAppliedDegrees = rotation,
          cropBoxSource = null,
          fallbackReasons = (listOf("upstream_crop_not_accepted") + reasons).distinct().sorted(),
        )
      }

      validateFullFrameBudget(source.width, source.height, source.width, source.height)
      return PreparedDocumentPixels(
        bitmap = renderGrayscaleFixedFrame(source, 0.0),
        decision = "full_frame_grayscale_fallback",
        rotationAppliedDegrees = 0.0,
        cropBoxSource = null,
        fallbackReasons = (listOf("upstream_crop_not_accepted") + reasons).distinct().sorted(),
      )
    }

    if (coordinateSpace != "deskewed_preview" || reasons.isNotEmpty()) {
      throw IllegalStateException("Accepted content-region contract is contradictory.")
    }
    val safePreview = parseBox(region["safeCropBounds"], previewWidth, previewHeight)
      ?: throw IllegalStateException("Accepted content region is missing safe crop bounds.")
    val candidate = parseBox(region["candidateContentBounds"], previewWidth, previewHeight)
      ?: throw IllegalStateException("Accepted content region is missing candidate bounds.")
    if (
      safePreview.left > candidate.left || safePreview.top > candidate.top ||
      safePreview.right < candidate.right || safePreview.bottom < candidate.bottom
    ) {
      throw IllegalStateException("Safe crop bounds do not contain candidate content bounds.")
    }

    val crop = mapToSource(safePreview, previewWidth, previewHeight, source.width, source.height)
    val sourcePixels = source.width.toLong() * source.height
    val cropPixels = crop.width.toLong() * crop.height
    val accounted = 4L * (sourcePixels + sourcePixels + cropPixels)
    if (accounted > PREPARED_MAX_ACCOUNTED_BYTES) {
      throw IllegalArgumentException("Prepared crop exceeds the bounded working-memory contract.")
    }

    val transformed = renderGrayscaleFixedFrame(source, rotation)
    try {
      val cropped = Bitmap.createBitmap(transformed, crop.left, crop.top, crop.width, crop.height)
      return PreparedDocumentPixels(
        bitmap = cropped,
        decision = "cropped_grayscale",
        rotationAppliedDegrees = rotation,
        cropBoxSource = crop.asList(),
        fallbackReasons = emptyList(),
      )
    } finally {
      if (!transformed.isRecycled) transformed.recycle()
    }
  }

  private fun expectedPreviewSize(width: Int, height: Int): Pair<Int, Int> {
    val scale = min(1.0, PREPARED_PREVIEW_LONG_SIDE.toDouble() / max(width, height))
    return max(1, (width * scale).roundToInt()) to max(1, (height * scale).roundToInt())
  }

  private fun parseBox(value: Any?, width: Int, height: Int): PreparedCropBox? {
    if (value == null) return null
    val values = (value as? List<*>)?.map { (it as? Number)?.toInt() }
      ?: throw IllegalStateException("Crop bounds are invalid.")
    if (values.size != 4 || values.any { it == null }) {
      throw IllegalStateException("Crop bounds are invalid.")
    }
    val (left, top, right, bottom) = values.map { it!! }
    if (!(0 <= left && left < right && right <= width && 0 <= top && top < bottom && bottom <= height)) {
      throw IllegalStateException("Crop bounds exceed the preview.")
    }
    return PreparedCropBox(left, top, right, bottom)
  }

  private fun mapToSource(
    box: PreparedCropBox,
    previewWidth: Int,
    previewHeight: Int,
    sourceWidth: Int,
    sourceHeight: Int,
  ): PreparedCropBox {
    val scaleX = sourceWidth.toDouble() / previewWidth
    val scaleY = sourceHeight.toDouble() / previewHeight
    val mapped = PreparedCropBox(
      max(0, floor(box.left * scaleX).toInt()),
      max(0, floor(box.top * scaleY).toInt()),
      min(sourceWidth, ceil(box.right * scaleX).toInt()),
      min(sourceHeight, ceil(box.bottom * scaleY).toInt()),
    )
    if (mapped.width <= 0 || mapped.height <= 0) {
      throw IllegalStateException("Mapped safe crop bounds are empty.")
    }
    return mapped
  }

  private fun predictedExpandedSize(width: Int, height: Int, rotationDegrees: Double): Pair<Int, Int> {
    if (abs(rotationDegrees) < 1e-9) return width to height
    val radians = Math.toRadians(rotationDegrees)
    val cosine = abs(cos(radians))
    val sine = abs(sin(radians))
    return max(1, ceil(width * cosine + height * sine).toInt()) to
      max(1, ceil(width * sine + height * cosine).toInt())
  }

  private fun validateFullFrameBudget(
    sourceWidth: Int,
    sourceHeight: Int,
    outputWidth: Int,
    outputHeight: Int,
  ) {
    if (max(outputWidth, outputHeight) > PREPARED_MAX_OUTPUT_LONG_SIDE) {
      throw IllegalArgumentException("Prepared full-frame output exceeds the bounded dimension contract.")
    }
    val sourcePixels = sourceWidth.toLong() * sourceHeight
    val outputPixels = outputWidth.toLong() * outputHeight
    val accounted = 4L * (sourcePixels + outputPixels)
    if (accounted > PREPARED_MAX_ACCOUNTED_BYTES) {
      throw IllegalArgumentException("Prepared full-frame grayscale exceeds the memory contract.")
    }
  }

  private fun grayscalePaint(): Paint =
    Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG).apply {
      colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setSaturation(0f) })
    }

  private fun renderGrayscaleFixedFrame(source: Bitmap, rotationDegrees: Double): Bitmap {
    val output = Bitmap.createBitmap(source.width, source.height, Bitmap.Config.ARGB_8888)
    output.eraseColor(Color.WHITE)
    val canvas = Canvas(output)
    val save = canvas.save()
    canvas.rotate(-rotationDegrees.toFloat(), source.width / 2f, source.height / 2f)
    canvas.drawBitmap(source, 0f, 0f, grayscalePaint())
    canvas.restoreToCount(save)
    return output
  }

  private fun renderGrayscaleExpandedFrame(
    source: Bitmap,
    rotationDegrees: Double,
    outputWidth: Int,
    outputHeight: Int,
  ): Bitmap {
    val output = Bitmap.createBitmap(outputWidth, outputHeight, Bitmap.Config.ARGB_8888)
    output.eraseColor(Color.WHITE)
    val canvas = Canvas(output)
    canvas.translate(outputWidth / 2f, outputHeight / 2f)
    canvas.rotate(-rotationDegrees.toFloat())
    canvas.translate(-source.width / 2f, -source.height / 2f)
    canvas.drawBitmap(source, 0f, 0f, grayscalePaint())
    return output
  }
}
