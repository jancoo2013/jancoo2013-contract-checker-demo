const assert = require("node:assert/strict");
const test = require("node:test");

const { mapImageBoxToContainedViewBox } = require("../.tmp-tests/overlayGeometry.js");

test("maps same aspect ratio without offsets", () => {
  assert.deepEqual(
    mapImageBoxToContainedViewBox(
      { x: 10, y: 20, width: 30, height: 40 },
      { width: 100, height: 200 },
      { width: 200, height: 400 },
    ),
    { x: 20, y: 40, width: 60, height: 80 },
  );
});

test("maps horizontal letterboxing with X offset", () => {
  assert.deepEqual(
    mapImageBoxToContainedViewBox(
      { x: 10, y: 10, width: 20, height: 20 },
      { width: 100, height: 100 },
      { width: 300, height: 100 },
    ),
    { x: 110, y: 10, width: 20, height: 20 },
  );
});

test("maps vertical letterboxing with Y offset", () => {
  assert.deepEqual(
    mapImageBoxToContainedViewBox(
      { x: 10, y: 10, width: 20, height: 20 },
      { width: 100, height: 100 },
      { width: 100, height: 300 },
    ),
    { x: 10, y: 110, width: 20, height: 20 },
  );
});

test("returns zero box for zero sizes", () => {
  assert.deepEqual(
    mapImageBoxToContainedViewBox(
      { x: 10, y: 10, width: 20, height: 20 },
      { width: 0, height: 100 },
      { width: 100, height: 100 },
    ),
    { x: 0, y: 0, width: 0, height: 0 },
  );
});
