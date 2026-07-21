export const CATEGORIES = Object.freeze(['missed_pii', 'incomplete_mask', 'over_redaction']);
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
export function displayBox([x0, y0, x1, y1], view, image) {
  const rect = contentRect(view.width, view.height, image.width, image.height);
  return {
    left: rect.x + x0 * rect.scale,
    top: rect.y + y0 * rect.scale,
    width: (x1 - x0) * rect.scale,
    height: (y1 - y0) * rect.scale,
  };
}
export function newSession(packKey, pages) {
  if (!packKey || !Array.isArray(pages) || !pages.length) throw new Error('pack and pages are required');
  return {
    packKey, pageIndex: 0, category: CATEGORIES[0], selectionError: null,
    pages: pages.map((page) => ({
      ...page,
      reviewRegions: page.reviewRegions || [],
      candidateMasks: page.candidateMasks || [],
      status: 'needs_review',
      findings: [],
    })),
  };
}
export function setPageIndex(session, index) {
  if (!Number.isInteger(index) || index < 0 || index >= session.pages.length) throw new Error('invalid page index');
  return { ...session, pageIndex: index, selectionError: null };
}
export function isComplete(session) {
  return session.pages.every((page) => page.status !== 'needs_review');
}
export function setCategory(session, category) {
  if (!CATEGORIES.includes(category)) throw new Error('invalid category');
  return { ...session, category, selectionError: null };
}
function contains([x0, y0, x1, y1], point) {
  return point.x >= x0 && point.x < x1 && point.y >= y0 && point.y < y1;
}
function selectTarget(page, category, point) {
  const targets = category === 'missed_pii' ? page.reviewRegions : page.candidateMasks;
  const direct = targets.find((target) => contains(target.box, point));
  if (direct || category !== 'missed_pii') return direct || null;
  const tolerance = Math.max(12, Math.round(page.height * 0.025));
  const distance = ([, y0, , y1]) => point.y < y0 ? y0 - point.y : point.y >= y1 ? point.y - y1 + 1 : 0;
  const nearest = targets.map((target) => ({ target, distance: distance(target.box) }))
    .sort((left, right) => left.distance - right.distance)[0];
  return nearest?.distance <= tolerance ? nearest.target : null;
}
export function addIssueTap(session, point) {
  if (!point) return session;
  const page = session.pages[session.pageIndex];
  const target = selectTarget(page, session.category, point);
  if (!target) {
    const selectionError = session.category === 'missed_pii'
      ? 'Коснитесь строки с пропущенными PII.'
      : 'Коснитесь существующей проблемной маски.';
    return { ...session, selectionError };
  }
  if (page.findings.some((item) => item.category === session.category && item.targetId === target.id)) {
    return { ...session, selectionError: 'Эта ошибка уже отмечена.' };
  }
  const pages = session.pages.map((item, index) => index === session.pageIndex ? {
    ...item,
    status: 'fail',
    findings: [...item.findings, { category: session.category, targetId: target.id, box: [...target.box] }],
  } : item);
  return { ...session, pages, selectionError: null };
}
export function setStatus(session, status) {
  if (!['pass', 'fail', 'needs_review'].includes(status)) throw new Error('invalid status');
  const page = session.pages[session.pageIndex];
  if (status === 'pass' && page.findings.length) throw new Error('pass page cannot contain findings');
  if (status === 'fail' && !page.findings.length) throw new Error('fail page requires findings');
  const pages = session.pages.map((item, index) => index === session.pageIndex ? { ...item, status } : item);
  return { ...session, pages, selectionError: null };
}
export function undoFinding(session) {
  const pages = session.pages.map((page, index) => index === session.pageIndex ? {
    ...page,
    status: page.findings.length <= 1 ? 'needs_review' : page.status,
    findings: page.findings.slice(0, -1),
  } : page);
  return { ...session, pages, selectionError: null };
}
export function reviewRows(session) {
  return session.pages.map((page) => ({
    schema_version: 1,
    pilot: 'controlled_pii_reviewer_v0',
    image_id: page.imageId,
    source_image_sha256: page.sourceSha256,
    derivative_image_sha256: page.derivativeSha256,
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
  return reviewRows(session).map((row) => JSON.stringify(sortObject(row))).join('\n') + '\n';
}
function sortObject(value) {
  if (Array.isArray(value)) return value.map(sortObject);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortObject(value[key])]));
}
