# Segment repair: frame-range fixes, bridges and seams

Agent checklist for replacing a bounded span of a finished clip, plus the seam practice that held up in tests.

## 1. Find and bound the defect

- Collect the review notes (timecode or frame, what is wrong). A saved review request is not permission to run a paid
  model.
- Look densely, not sparsely: a 24-frame filmstrip around every cut, seam and suspect span
  (`ffmpeg -ss S -to E -i clip.mp4 -vf "fps=N,scale=320:-1,tile=6x4" -frames:v 1 strip.png`). Sparse contact sheets
  have missed a sliding mouth that was obvious in motion.
- Ranges are zero-based `[start, end)` frames. Choose cut points on motion pauses where possible.

## 2. Prepare the package (CPU, no GPU yet)

Write a folder `repair-<id>/` with: the first and last boundary frames (PNG), a lossless control clip of the span with
handles (e.g. 4 frames each side, FFV1), the source hash, the prompt, the chosen route and a `repair.json` replacement
contract (`source`, `source_sha256`, `start`, `end`, `handles`, `fps`, `size`, `route`). Handles widen the model input;
only `[start, end)` is inserted back. Prepared is not generated.

## 3. Choose the route

| Defect | Route | Inputs |
|---|---|---|
| Broken transition / jump between two good frames | Wan FLF; H3 FLF (+ depth) on a scene where it already worked | the two boundary frames, camera/motion prompt, fixed identity reference |
| Motion is right, look/detail is wrong | VACE v2v | control clip, same geometry, strength per task |
| Only a region is wrong (face, hand, logo, artefact) | VACE inpaint | tracked mask (WHITE = regenerate, BLACK = keep), same fps/size/frame count; composite protected pixels back |
| Identity drift (face/body) | VACE inpaint on a face/body mask with the character sheet as reference; face restorers (CodeFormer) only as a last resort (plastic look) | sheet, mask |
| Scene continues past the end | next segment from the last accepted frame plus overlap, constant identity reference; for long takes prefer SVI | never chain defective frames forward; last-frame-only continuation degrades after 2-3 hops |
| Lip-sync wrong in a talking shot | LatentSync or InfiniteTalk on the whole shot | see lessons below |

Wan/VACE need `4n+1` frames (H3 Ref2VA `17n+5`). Never retime the master for a model: conform a **copy of the
candidate** to the segment contract (size, fps, frame count). Run under the GPU lock.

## 4. Fix the seams of generated segments

- FLF chains between spine keyframes have exact seams because segment N ends on the image segment N+1 starts with;
  drift stays inside segments. Drop one duplicated boundary frame when joining.
- Colour-match each segment to its spine keyframe (histogram or LAB mean/std) before joining.
- Residual seam: a 4-8 frame crossfade, or regenerate ~16 frames across the seam with VACE using both sides as context
  (a v2v package centred on the seam with handles).
- One continuous audio bed over the joined take, not per segment.

## 5. Review and assemble

- Save the run receipt and the candidate. Review the whole span in motion (H.264 MP4 for a browser; FFV1/MKV may not
  play): identity, first/last frames, background, hands/face, mask edge, then a filmstrip across both joins.
- After the operator picks a variant, build a **separate** candidate master (e.g. FFV1 + source audio as PCM in MKV).
  Check that decoded frames outside the range equal the original and frames inside equal the trimmed candidate
  (per-frame hashes via `ffmpeg -f framemd5`), and that audio samples are unchanged. A technical pass does not replace
  watching the seams.
- Limits worth enforcing: SDR, square pixels, one video track, CFR. Refuse VFR/HDR/rotated sources (prepare a CFR copy
  first). No hidden tonemap, no audio retime, no cloud fallback, no automatic retries.

## Lessons from tests (lip-sync repair)

- A lower-face patch aligned by upper-face affine registration made the mouth slide off the face; it passed a sparse
  contact sheet and failed in motion. Check mask coverage first and review densely.
- Prefer a whole-shot replacement from a take that already has correct articulation over a regional composite or a
  mid-word jump cut; cut only at a real pause (scan the audio for one first).
- Record the rejection in the receipt; keep the rejected candidate as evidence.
- A queued delivery message is not delivery; check the delivery receipt and never resend automatically.
