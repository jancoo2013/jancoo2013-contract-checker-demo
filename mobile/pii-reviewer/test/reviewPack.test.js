import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { loadReviewPack, parseJsonl, pngInfo, safePath } from '../src/reviewPack.js';

const enc = new TextEncoder();
const sha = async (bytes) => createHash('sha256').update(bytes).digest('hex');
function png(width=20,height=30,color=0) {
  const bytes = new Uint8Array(29); bytes.set([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]);
  const put=(o,n)=>{ bytes[o]=(n>>>24)&255; bytes[o+1]=(n>>>16)&255; bytes[o+2]=(n>>>8)&255; bytes[o+3]=n&255; };
  put(16,width); put(20,height); bytes[24]=8; bytes[25]=color; return bytes;
}
function jsonl(rows) { return enc.encode(rows.map((row)=>JSON.stringify(row)).join('\n')+'\n'); }
async function fixture() {
  const source=png(), derivative=png(), sourceSha=await sha(source), derivativeSha=await sha(derivative);
  const prediction={schema_version:1,algorithm:'marker_layout_baseline_v0',image_id:'P0001',image:'sources/P0001.png',image_sha256:sourceSha,width:20,height:30,candidates:[{candidate_id:'P0001-C0001',proposed_class:'person_name',geometry:{type:'bbox',coordinates:[1,2,10,8]},review_status:'needs_review',reason_codes:['party_header_zone']}]};
  const predictionBytes=jsonl([prediction]), predictionSha=await sha(predictionBytes);
  const renderer={schema_version:1,renderer:'grayscale_opaque_mask_v0',image_id:'P0001',source_image_sha256:sourceSha,prediction_manifest_sha256:predictionSha,derivative_image:'images/P0001.png',derivative_sha256:derivativeSha,width:20,height:30,mode:'L',mask_value:0,mask_count:1,masked_pixel_count:54};
  const line={schema_version:1,page_id:'P0001',line_id:'P0001-L0001',order:1,bbox:[0,1,20,9],bbox_convention:'xyxy_half_open',segmentation_status:'accepted',status:'accepted',reasons:[],upstream_resolution_status:'accepted',foreground_pixels:20,line_image:'lines/x.png',line_sha256:'3'.repeat(64),source_master_sha256:sourceSha};
  const files=new Map([['predictions.jsonl',predictionBytes],['renderer/manifest.jsonl',jsonl([renderer])],['line_segmentation/manifest.jsonl',jsonl([line])],['sources/P0001.png',source],['renderer/images/P0001.png',derivative]]);
  const read=async(path,limit)=>{ const bytes=files.get(path); if(!bytes) throw new Error(`missing ${path}`); if(bytes.length>limit) throw new Error('limit'); return {bytes,uri:`content://${path}`}; };
  const imageSize=async()=>({width:20,height:30});
  const snapshotNames=[];
  const snapshot=async(_bytes,name)=>{ snapshotNames.push(name); return `memory://${name}`; };
  return { files, read, predictionSha, imageSize, snapshot, snapshotNames };
}

test('safe paths reject traversal and backslashes',()=>{ assert.equal(safePath('a/b.png'),'a/b.png'); for(const value of ['../x','/x','a\\b','a//b','./x']) assert.throws(()=>safePath(value)); });
test('JSONL rejects blanks and malformed UTF-8',()=>{ assert.equal(parseJsonl(enc.encode('{"x":1}\n'),'x').length,1); assert.throws(()=>parseJsonl(enc.encode('{"x":1}\n\n'),'x')); assert.throws(()=>parseJsonl(new Uint8Array([255]),'x')); });
test('PNG identity enforces grayscale derivative',()=>{ assert.deepEqual(pngInfo(png(20,30),'x',true),{width:20,height:30}); assert.throws(()=>pngInfo(png(20,30,6),'x',true)); });
test('valid pack binds manifests, hashes, lines and PNG snapshot names',async()=>{ const {read,predictionSha,imageSize,snapshot,snapshotNames}=await fixture(); const pack=await loadReviewPack(read,sha,imageSize,snapshot); assert.equal(pack.packKey,predictionSha); assert.deepEqual(pack.pages[0].candidateMasks[0].box,[1,2,10,8]); assert.equal(pack.pages[0].reviewRegions[0].id,'P0001-L0001'); assert.equal(pack.pages[0].sourceUri,'memory://P0001-source.png'); assert.deepEqual(snapshotNames,['P0001-source.png','P0001-derivative.png']); });
test('hash and renderer binding mismatches fail closed',async()=>{ const one=await fixture(); one.files.set('sources/P0001.png',png(21,30)); await assert.rejects(()=>loadReviewPack(one.read,sha,one.imageSize,one.snapshot),/hash mismatch/); const two=await fixture(); const rows=parseJsonl(two.files.get('renderer/manifest.jsonl'),'x'); rows[0].prediction_manifest_sha256='0'.repeat(64); two.files.set('renderer/manifest.jsonl',jsonl(rows)); await assert.rejects(()=>loadReviewPack(two.read,sha,two.imageSize,two.snapshot),/renderer binding mismatch/); });
test('duplicate or unknown line identity fails closed',async()=>{ const one=await fixture(); const rows=parseJsonl(one.files.get('line_segmentation/manifest.jsonl'),'x'); one.files.set('line_segmentation/manifest.jsonl',jsonl([rows[0],rows[0]])); await assert.rejects(()=>loadReviewPack(one.read,sha,one.imageSize,one.snapshot),/duplicate|invalid identity/); const two=await fixture(); const row=parseJsonl(two.files.get('line_segmentation/manifest.jsonl'),'x')[0]; row.page_id='P9999'; row.line_id='P9999-L0001'; two.files.set('line_segmentation/manifest.jsonl',jsonl([row])); await assert.rejects(()=>loadReviewPack(two.read,sha,two.imageSize,two.snapshot),/unknown page/); });
