export const CATEGORIES = Object.freeze([
  'missed_pii',
  'incomplete_mask',
  'over_redaction',
]);

export function contentRect(viewWidth, viewHeight, imageWidth, imageHeight) {
  if ([viewWidth, viewHeight, imageWidth, imageHeight].some((value) => !Number.isFinite(value) || value <= 0)) {
    throw new Error('dimensions must be positive finite numbers');
  }
  const scale = Math.min(viewWidth / imageWidth, viewHeight / imageHeight);
  const width = imageWidth * scale;
  const height = imageHeight * scale;
  return { x: (viewWidth - width) / 2, y: (viewHeight - height) / 2, width, height, scale };
}

export function imagePoint(touch, view, image) {
  const rect = contentRect(view.width, view.height, image.width, image.height);
  const x = Math.round((touch.x - rect.x) / rect.scale);
  const y = Math.round((touch.y - rect.y) / rect.scale);
  if (x < 0 || y < 0 || x > image.width || y > image.height) return null;
  return { x: Math.min(x, image.width), y: Math.min(y, image.height) };
}

export function displayBox(box, view, image) {
  const rect = contentRect(view.width, view.height, image.width, image.height);
  const [x0, y0, x1, y1] = box;
  return {
    left: rect.x + x0 * rect.scale,
    top: rect.y + y0 * rect.scale,
    width: (x1 - x0) * rect.scale,
    height: (y1 - y0) * rect.scale,
  };
}

export function newSession(packKey, pages) {
  if (!packKey || !Array.isArray(pages) || pages.length === 0) throw new Error('pack and pages are required');
  return {
    packKey,
    pageIndex: 0,
    category: CATEGORIES[0],
    firstPoint: null,
    pages: pages.map((page) => ({ ...page, status: 'needs_review', findings: [] })),
  };
}

export function addTap(session, point) {
  if (!point) return session;
  if (!session.firstPoint) return { ...session, firstPoint: point };
  const x0 = Math.min(session.firstPoint.x, point.x);
  const y0 = Math.min(session.firstPoint.y, point.y);
  const x1 = Math.max(session.firstPoint.x, point.x);
  const y1 = Math.max(session.firstPoint.y, point.y);
  if (x0 === x1 || y0 === y1) return { ...session, firstPoint: null };
  const pages = session.pages.map((page, index) => index === session.pageIndex ? {
    ...page,
    status: 'fail',
    findings: [...page.findings, { category: session.category, box: [x0, y0, x1, y1] }],
  } : page);
  return { ...session, pages, firstPoint: null };
}

export function setStatus(session, status) {
  if (!['pass', 'fail', 'needs_review'].includes(status)) throw new Error('invalid status');
  const page = session.pages[session.pageIndex];
  if (status === 'pass' && page.findings.length) throw new Error('pass page cannot contain findings');
  if (status === 'fail' && !page.findings.length) throw new Error('fail page requires findings');
  const pages = session.pages.map((item, index) => index === session.pageIndex ? { ...item, status } : item);
  return { ...session, pages, firstPoint: null };
}

export function undoFinding(session) {
  const pages = session.pages.map((page, index) => index === session.pageIndex ? {
    ...page,
    status: page.findings.length <= 1 ? 'needs_review' : page.status,
    findings: page.findings.slice(0, -1),
  } : page);
  return { ...session, pages, firstPoint: null };
}

export function reviewRows(session) {
  return session.pages.map((page) => ({
    schema_version: 1,
    image_id: page.imageId,
    source_image_sha256: page.sourceSha256,
    derivative_sha256: page.derivativeSha256,
    prediction_manifest_sha256: session.packKey,
    width: page.width,
    height: page.height,
    page_status: page.status,
    findings: page.findings.map((finding, index) => ({
      finding_id: `${page.imageId}-F${String(index + 1).padStart(4, '0')}`,
      category: finding.category,
      geometry: { type: 'bbox', coordinates: finding.box },
    })),
  }));
}

export function canonicalJsonl(session) {
  return reviewRows(session)
    .map((row) => JSON.stringify(sortObject(row)))
    .join('\n') + '\n';
}

function sortObject(value) {
  if (Array.isArray(value)) return value.map(sortObject);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortObject(value[key])]));
}
