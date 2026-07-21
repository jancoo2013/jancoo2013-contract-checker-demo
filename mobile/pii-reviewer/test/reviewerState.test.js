import test from 'node:test';
import assert from 'node:assert/strict';
import {
  addTap,
  canonicalJsonl,
  contentRect,
  imagePoint,
  newSession,
  reviewRows,
  setStatus,
  undoFinding,
} from '../src/reviewerState.js';

const page = {
  imageId: 'P0001',
  sourceSha256: '1'.repeat(64),
  derivativeSha256: '2'.repeat(64),
  width: 1000,
  height: 1400,
};

test('contain geometry maps touch coordinates to image pixels', () => {
  const rect = contentRect(500, 500, 1000, 1400);
  assert.deepEqual(rect, { x: 71.42857142857142, y: 0, width: 357.14285714285717, height: 500, scale: 0.35714285714285715 });
  assert.deepEqual(imagePoint({ x: rect.x, y: 0 }, { width: 500, height: 500 }, page), { x: 0, y: 0 });
  assert.equal(imagePoint({ x: 0, y: 0 }, { width: 500, height: 500 }, page), null);
});

test('two taps create canonical half-open bbox and fail status', () => {
  let session = newSession('a'.repeat(64), [page]);
  session = addTap(session, { x: 90, y: 300 });
  session = addTap(session, { x: 10, y: 20 });
  assert.deepEqual(session.pages[0].findings[0].box, [10, 20, 90, 300]);
  assert.equal(session.pages[0].status, 'fail');
});

test('page status invariants are fail closed', () => {
  const empty = newSession('a'.repeat(64), [page]);
  assert.throws(() => setStatus(empty, 'fail'), /requires findings/);
  const failed = addTap(addTap(empty, { x: 1, y: 1 }), { x: 2, y: 2 });
  assert.throws(() => setStatus(failed, 'pass'), /cannot contain findings/);
  assert.equal(setStatus(empty, 'pass').pages[0].status, 'pass');
});

test('undo clears last finding and restores needs_review', () => {
  let session = newSession('a'.repeat(64), [page]);
  session = addTap(addTap(session, { x: 1, y: 1 }), { x: 3, y: 4 });
  session = undoFinding(session);
  assert.equal(session.pages[0].findings.length, 0);
  assert.equal(session.pages[0].status, 'needs_review');
});

test('manifest rows and JSONL are deterministic', () => {
  let session = newSession('a'.repeat(64), [page]);
  session = addTap(addTap(session, { x: 1, y: 1 }), { x: 3, y: 4 });
  const rows = reviewRows(session);
  assert.equal(rows[0].findings[0].finding_id, 'P0001-F0001');
  assert.equal(canonicalJsonl(session), canonicalJsonl(session));
  assert.match(canonicalJsonl(session), /"page_status":"fail"/);
});
