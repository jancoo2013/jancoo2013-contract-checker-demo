import test from 'node:test';
import assert from 'node:assert/strict';
import {
  addIssueTap, canonicalJsonl, contentRect, imagePoint, isComplete, newSession,
  reviewRows, setCategory, setPageIndex, setStatus, undoFinding,
} from '../src/reviewerState.js';
const page = {
  imageId: 'P0001', sourceSha256: '1'.repeat(64), derivativeSha256: '2'.repeat(64),
  width: 1000, height: 1400,
  reviewRegions: [
    { id: 'line-1', box: [100, 100, 900, 140] },
    { id: 'line-2', box: [100, 180, 900, 220] },
  ],
  candidateMasks: [
    { id: 'mask-1', box: [120, 100, 880, 140] },
    { id: 'mask-2', box: [600, 1180, 900, 1255] },
  ],
};
test('contain geometry maps touch coordinates to image pixels', () => {
  const rect = contentRect(500, 500, 1000, 1400);
  assert.deepEqual(rect, { x: 71.42857142857142, y: 0, width: 357.14285714285717, height: 500, scale: 0.35714285714285715 });
  assert.deepEqual(imagePoint({ x: rect.x, y: 0 }, { width: 500, height: 500 }, page), { x: 0, y: 0 });
  assert.equal(imagePoint({ x: 0, y: 0 }, { width: 500, height: 500 }, page), null);
});
test('missed PII tap snaps to a predefined review line', () => {
  const session = addIssueTap(newSession('a'.repeat(64), [page]), { x: 500, y: 150 });
  assert.deepEqual(session.pages[0].findings[0].box, [100, 100, 900, 140]);
  assert.equal(session.pages[0].status, 'fail');
});
test('mask findings select an existing mask with one tap', () => {
  let session = setCategory(newSession('a'.repeat(64), [page]), 'incomplete_mask');
  session = addIssueTap(session, { x: 500, y: 120 });
  assert.deepEqual(session.pages[0].findings[0].box, [120, 100, 880, 140]);
  session = addIssueTap(session, { x: 300, y: 700 });
  assert.equal(session.pages[0].findings.length, 1);
  assert.match(session.selectionError, /маски/);
});
test('duplicate target/category is ignored', () => {
  let session = newSession('a'.repeat(64), [page]);
  session = addIssueTap(session, { x: 500, y: 110 });
  session = addIssueTap(session, { x: 500, y: 110 });
  assert.equal(session.pages[0].findings.length, 1);
  assert.match(session.selectionError, /уже отмечена/);
});
test('page status invariants and undo are fail closed', () => {
  const empty = newSession('a'.repeat(64), [page]);
  assert.throws(() => setStatus(empty, 'fail'), /requires findings/);
  const failed = addIssueTap(empty, { x: 500, y: 110 });
  assert.throws(() => setStatus(failed, 'pass'), /cannot contain findings/);
  assert.equal(setStatus(empty, 'pass').pages[0].status, 'pass');
  assert.equal(undoFinding(failed).pages[0].status, 'needs_review');
});
test('page navigation and completion are fail closed', () => {
  const second = { ...page, imageId: 'P0002' };
  let session = setStatus(newSession('a'.repeat(64), [page, second]), 'pass');
  session = setPageIndex(session, 1);
  assert.equal(isComplete(session), false);
  assert.equal(isComplete(setStatus(session, 'pass')), true);
  assert.throws(() => setPageIndex(session, 2), /invalid page/);
});
test('manifest matches Python pilot schema and omits target metadata', () => {
  const session = addIssueTap(newSession('a'.repeat(64), [page]), { x: 500, y: 110 });
  const row = reviewRows(session)[0];
  assert.equal(row.pilot, 'controlled_pii_reviewer_v0');
  assert.equal(row.derivative_image_sha256, '2'.repeat(64));
  assert.equal(row.derivative_sha256, undefined);
  assert.equal(row.findings[0].targetId, undefined);
  assert.deepEqual(row.findings[0].geometry.coordinates, [100, 100, 900, 140]);
  assert.equal(canonicalJsonl(session), canonicalJsonl(session));
});
