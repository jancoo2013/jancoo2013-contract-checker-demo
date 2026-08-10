package expo.modules.documentgeometrypreview

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
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
import kotlin.math.max
import kotlin.math.roundToInt

private const val PREVIEW_LONG_SIDE = 1800
private const val MAX_SOURCE_LONG_SIDE = 8192
private const val MAX_SOURCE_PIXELS = 32_000_000L
private const val MAX_SOURCE_BYTES = 48L * 1024L * 1024L

class DocumentGeometryPreviewModule : Module() {
  private val context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  override fun definition() = ModuleDefinition {
    Name("DocumentGeometryPreview")
    AsyncFunction("buildPreviewAsync") Coroutine { uriString: String -> buildPreview(uriString) }
  }

  private fun prepareCache(): File {
    val root = File(context.cacheDir, "document-geometry-preview")
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
