const MANIFEST_LIMIT = 8 * 1024 * 1024, IMAGE_LIMIT = 64 * 1024 * 1024, MAX_PIXELS = 4096 * 4096;
const SHA = /^[0-9a-f]{64}$/, ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const PII_CLASSES = new Set(['person_name','israeli_id','phone','email','property_address','other_address','signature','initials','stamp','bank_identifier','cheque_identifier','handwritten_identifier','other_likely_pii']);
const REASONS = new Set(['party_header_zone','property_address_zone','signature_zone','right_label_shape','digit_pattern','segmentation_review']);
const PRED_KEYS = ['algorithm','candidates','height','image','image_id','image_sha256','schema_version','width'], CAND_KEYS = ['candidate_id','geometry','proposed_class','reason_codes','review_status'];
const DERIV_KEYS = ['derivative_image','derivative_sha256','height','image_id','mask_count','mask_value','masked_pixel_count','mode','prediction_manifest_sha256','renderer','schema_version','source_image_sha256','width'];
const LINE_KEYS = ['bbox','bbox_convention','foreground_pixels','line_id','line_image','line_sha256','order','page_id','reasons','schema_version','segmentation_status','source_master_sha256','status','upstream_resolution_status'];
function exact(row, keys, label) { if (!row || typeof row !== 'object' || Array.isArray(row) || Object.keys(row).sort().join('|') !== keys.join('|')) throw new Error(`${label}: invalid fields`); }
function integer(value) { return Number.isInteger(value) && typeof value !== 'boolean'; }
function bbox(value, width, height, label) {
  if (!Array.isArray(value) || value.length !== 4 || !value.every(integer)) throw new Error(`${label}: invalid bbox`); const [x0,y0,x1,y1] = value;
  if (!(0 <= x0 && x0 < x1 && x1 <= width && 0 <= y0 && y0 < y1 && y1 <= height)) throw new Error(`${label}: bbox out of bounds`);
  return [...value];
}
export function safePath(value) {
  if (typeof value !== 'string' || !value || value.startsWith('/') || value.includes('\\')) throw new Error('unsafe relative path'); const parts = value.split('/');
  if (parts.some((part) => !part || part === '.' || part === '..')) throw new Error('unsafe relative path'); return parts.join('/');
}
export function parseJsonl(bytes, label) {
  if (!(bytes instanceof Uint8Array) || !bytes.length || bytes.length > MANIFEST_LIMIT) throw new Error(`${label}: invalid size`);
  let text; try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); } catch { throw new Error(`${label}: invalid UTF-8`); }
  const lines = text.split(/\r?\n/); if (lines.at(-1) === '') lines.pop();
  if (!lines.length || lines.some((line) => !line.trim())) throw new Error(`${label}: blank or empty line`);
  return lines.map((line, index) => { try { return JSON.parse(line); } catch { throw new Error(`${label}: invalid JSON at ${index + 1}`); } });
}
export function pngInfo(bytes, label, grayscale = false) {
  const sig = [137,80,78,71,13,10,26,10];
  if (!(bytes instanceof Uint8Array) || bytes.length < 29 || sig.some((n,i) => bytes[i] !== n) || String.fromCharCode(...bytes.slice(12,16)) !== 'IHDR') throw new Error(`${label}: invalid PNG`);
  const read = (offset) => ((bytes[offset] << 24) >>> 0) + (bytes[offset+1] << 16) + (bytes[offset+2] << 8) + bytes[offset+3];
  const width = read(16), height = read(20);
  if (!width || !height || width * height > MAX_PIXELS) throw new Error(`${label}: invalid PNG dimensions`);
  if (grayscale && (bytes[24] !== 8 || bytes[25] !== 0)) throw new Error(`${label}: derivative must be 8-bit grayscale PNG`);
  return { width, height };
}
function geometry(candidate, width, height, label) {
  const value = candidate.geometry; if (!value || Object.keys(value).sort().join('|') !== 'coordinates|type' || value.type !== 'bbox') throw new Error(`${label}: invalid geometry`);
  return bbox(value.coordinates, width, height, label);
}
export async function loadReviewPack(read, sha256, imageSize, snapshot) {
  const prediction = await read('predictions.jsonl', MANIFEST_LIMIT), predictionSha = await sha256(prediction.bytes);
  const predictions = parseJsonl(prediction.bytes, 'predictions');
  const derivatives = parseJsonl((await read('renderer/manifest.jsonl', MANIFEST_LIMIT)).bytes, 'renderer manifest');
  const lines = parseJsonl((await read('line_segmentation/manifest.jsonl', MANIFEST_LIMIT)).bytes, 'line manifest');
  if (predictions.length !== derivatives.length) throw new Error('prediction/renderer page counts differ');
  const lineGroups = new Map(), lineIds = new Set();
  for (const [index, line] of lines.entries()) {
    exact(line, LINE_KEYS, `line ${index + 1}`);
    if (line.schema_version !== 1 || !ID.test(line.page_id) || !ID.test(line.line_id) || lineIds.has(line.line_id) || line.bbox_convention !== 'xyxy_half_open' || !integer(line.order) || line.order <= 0 || !Array.isArray(line.reasons) || line.reasons.some((x) => typeof x !== 'string') || !SHA.test(line.source_master_sha256)) throw new Error(`line ${index + 1}: invalid identity`);
    lineIds.add(line.line_id); const group = lineGroups.get(line.page_id) || []; group.push(line); lineGroups.set(line.page_id, group);
  }
  const pages = [], imageIds = new Set(), candidateIds = new Set();
  for (let index = 0; index < predictions.length; index += 1) {
    const p = predictions[index], d = derivatives[index]; exact(p, PRED_KEYS, `prediction ${index + 1}`); exact(d, DERIV_KEYS, `derivative ${index + 1}`);
    const { image_id: id, width, height } = p;
    if (p.schema_version !== 1 || p.algorithm !== 'marker_layout_baseline_v0' || !ID.test(id) || imageIds.has(id) || !integer(width) || !integer(height) || width <= 0 || height <= 0 || width * height > MAX_PIXELS || !SHA.test(p.image_sha256) || !Array.isArray(p.candidates)) throw new Error(`${id || index}: invalid prediction`);
    imageIds.add(id);
    const masks = p.candidates.map((candidate, n) => {
      exact(candidate, CAND_KEYS, `${id}/candidate ${n + 1}`);
      if (!ID.test(candidate.candidate_id) || candidateIds.has(candidate.candidate_id) || candidate.review_status !== 'needs_review' || !PII_CLASSES.has(candidate.proposed_class) || !Array.isArray(candidate.reason_codes) || candidate.reason_codes.some((x) => typeof x !== 'string' || !REASONS.has(x)) || new Set(candidate.reason_codes).size !== candidate.reason_codes.length) throw new Error(`${id}/candidate ${n + 1}: invalid identity`);
      candidateIds.add(candidate.candidate_id); return { id: candidate.candidate_id, box: geometry(candidate, width, height, `${id}/candidate ${n + 1}`) };
    });
    if (d.schema_version !== 1 || d.renderer !== 'grayscale_opaque_mask_v0' || d.image_id !== id || d.source_image_sha256 !== p.image_sha256 || d.prediction_manifest_sha256 !== predictionSha || d.width !== width || d.height !== height || d.mode !== 'L' || d.mask_value !== 0 || d.mask_count !== masks.length || !integer(d.masked_pixel_count) || d.masked_pixel_count < 0 || d.masked_pixel_count > width * height || !SHA.test(d.derivative_sha256)) throw new Error(`${id}: renderer binding mismatch`);
    const source = await read(safePath(p.image), IMAGE_LIMIT), derivative = await read(`renderer/${safePath(d.derivative_image)}`, IMAGE_LIMIT);
    if (await sha256(source.bytes) !== p.image_sha256 || await sha256(derivative.bytes) !== d.derivative_sha256) throw new Error(`${id}: image hash mismatch`);
    const sourceUri = await snapshot(source.bytes, `${id}-source.png`, predictionSha);
    const derivativeUri = await snapshot(derivative.bytes, `${id}-derivative.png`, predictionSha);
    const sourceInfo = await imageSize(sourceUri), derivativeInfo = pngInfo(derivative.bytes, `${id} derivative`, true);
    if (sourceInfo.width !== width || sourceInfo.height !== height || derivativeInfo.width !== width || derivativeInfo.height !== height) throw new Error(`${id}: image dimensions mismatch`);
    const pageLines = (lineGroups.get(id) || []).sort((a,b) => a.order - b.order);
    if (pageLines.some((line, n) => line.order !== n + 1 || line.source_master_sha256 !== p.image_sha256)) throw new Error(`${id}: line binding mismatch`);
    pages.push({ imageId:id, sourceSha256:p.image_sha256, derivativeSha256:d.derivative_sha256, width, height, sourceUri, derivativeUri, candidateMasks:masks, reviewRegions:pageLines.map((line) => ({ id:line.line_id, box:bbox(line.bbox,width,height,line.line_id) })) });
  }
  if ([...lineGroups.keys()].some((id) => !imageIds.has(id))) throw new Error('line manifest contains unknown page');
  return { packKey: predictionSha, pages };
}
