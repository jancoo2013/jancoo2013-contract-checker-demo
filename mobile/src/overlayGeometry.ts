export type Box = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type Size = {
  width: number;
  height: number;
};

export function mapImageBoxToContainedViewBox(
  box: Box,
  imageSize: Size,
  viewSize: Size,
): Box {
  if (
    imageSize.width <= 0 ||
    imageSize.height <= 0 ||
    viewSize.width <= 0 ||
    viewSize.height <= 0
  ) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }

  const scale = Math.min(viewSize.width / imageSize.width, viewSize.height / imageSize.height);
  const renderedWidth = imageSize.width * scale;
  const renderedHeight = imageSize.height * scale;
  const offsetX = (viewSize.width - renderedWidth) / 2;
  const offsetY = (viewSize.height - renderedHeight) / 2;

  return {
    x: offsetX + box.x * scale,
    y: offsetY + box.y * scale,
    width: box.width * scale,
    height: box.height * scale,
  };
}
