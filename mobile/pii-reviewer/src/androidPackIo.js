import { Image } from 'react-native';
import * as Crypto from 'expo-crypto';
import { Directory, File, Paths } from 'expo-file-system';
import { loadReviewPack, safePath } from './reviewPack';
import { canonicalJsonl, isComplete } from './reviewerState';
let activeRoot = null, activePackKey = null, activeCache = null;
async function digest(bytes) { const value = await Crypto.digest(Crypto.CryptoDigestAlgorithm.SHA256, bytes); return [...new Uint8Array(value)].map((byte) => byte.toString(16).padStart(2, '0')).join(''); }
function dimensions(uri) { return new Promise((resolve, reject) => Image.getSize(uri, (width, height) => resolve({ width, height }), reject)); }
async function snapshot(bytes, name, packKey) {
  const directory = new Directory(Paths.cache, 'pii-reviewer-packs', packKey);
  directory.create({ idempotent: true, intermediates: true });
  const file = new File(directory, name); file.create({ overwrite: true }); file.write(bytes);
  const saved = await file.bytes();
  if (saved.length !== bytes.length || await digest(saved) !== await digest(bytes)) { try { file.delete(); } catch {} throw new Error('verified image snapshot failed'); }
  return file.uri;}
async function readRelative(root, relative, limit) {
  const parts = safePath(relative).split('/');
  let directory = root;
  for (let index = 0; index < parts.length; index += 1) {
    const matches = directory.list().filter((entry) => entry.name === parts[index]);
    if (matches.length !== 1) throw new Error(`missing or ambiguous pack path: ${relative}`);
    const entry = matches[0], last = index === parts.length - 1;
    if (last && !(entry instanceof File)) throw new Error(`pack path is not a file: ${relative}`);
    if (!last && !(entry instanceof Directory)) throw new Error(`pack path is not a directory: ${relative}`);
    if (last) {
      if (!entry.exists || entry.size > limit) throw new Error(`pack file is missing or too large: ${relative}`);
      const bytes = await entry.bytes();
      if (bytes.length > limit) throw new Error(`pack file is too large: ${relative}`);
      return { bytes, uri: entry.uri };
    }
    directory = entry;
  }
  throw new Error(`invalid pack path: ${relative}`);
}
export async function pickReviewPack() {
  const root = await Directory.pickDirectoryAsync(); if (!root) return null;
  const pack = await loadReviewPack((path, limit) => readRelative(root, path, limit), digest, dimensions, snapshot);
  const previous = activeCache; activeRoot = root; activePackKey = pack.packKey; activeCache = new Directory(Paths.cache, 'pii-reviewer-packs', pack.packKey);
  if (previous && previous.uri !== activeCache.uri) { try { previous.delete(); } catch {} }
  return pack;
}
export async function saveReviewResult(session) {
  if (!activeRoot || session.packKey !== activePackKey) throw new Error('review pack is not active');
  if (!isComplete(session)) throw new Error('all pages must be reviewed before saving');
  const file = new File(activeRoot, `review-${session.packKey}.jsonl`);
  let created = false;
  try {
    file.create({ overwrite: false }); created = true;
    const payload = canonicalJsonl(session); file.write(payload);
    if (await file.text() !== payload) throw new Error('saved review changed during publication');
    return file.uri;
  } catch (error) {
    if (created) { try { file.delete(); } catch {} }
    throw error;
  }
}
