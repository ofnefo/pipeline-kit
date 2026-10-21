# Image preparation and integration

## Contents

1. Choose the right source
2. Generate or edit
3. Background removal and masks
4. Integrate multiple images
5. Raster-to-vector decisions
6. Resolution and enlargement
7. Image QA

## 1. Choose the right source

Select imagery against the intended crop and composition, not in isolation. Check:

- subject direction and available negative space;
- horizon and camera height;
- perspective and lens character;
- light direction, softness, and temperature;
- detail scale relative to the final banner;
- licensing and whether the file is approved for production.

A mediocre source with the correct pose, crop, and light can integrate better than a spectacular source that fights the layout.

## 2. Generate or edit

Use image generation for new decorative architecture, textures, atmospheres, or illustrations when approved source material is missing. Request:

- the intended crop/aspect ratio;
- explicit negative-space location;
- clean subject separation and edge behavior;
- matching camera height, light, materials, and palette;
- no text, logo, signage, watermark, or pseudo-brand marks.

Use image editing rather than regeneration when identity, geometry, or exact source content must remain. Do not ask a generative model to reproduce an official logo, exact building, product, or final copy.

## 3. Background removal and masks

Route execution and editable-mask delivery to `$photoshop-production`; use this section to choose the image method within the larger composition workflow.

Choose the method by edge type:

- **Photoshop Device Select Subject:** first choice for difficult local raster work and white-on-white architecture.
- **Illustrator Remove Background:** second Adobe raster opinion for placed images.
- **BiRefNet/InSPyReNet/BEN2:** open-weight local alternatives; prove on the same image before committing.
- **ViTMatte:** refine a useful trimap; it cannot restore foreground omitted by the initial segmentation.
- **Known-color key:** flat controlled backgrounds when semantic models delete pale foreground.
- **Manual pen/channel mask:** exact hard products, logos, architecture, or when automation fails.

Preserve a non-destructive mask in the editable source. Keep the original image and raw model mask. Do not destructively erase production pixels.

Inspect masks on white, black, 50% gray, and the final background. Look for white/black fringe, semi-transparent solid surfaces, dirty RGB in transparent pixels, missing holes, stair-stepping, and lost thin structures.

## 4. Integrate multiple images

Match in this order:

1. crop and subject scale;
2. perspective, camera height, and horizon;
3. light direction and shadow logic;
4. black/white points and local contrast;
5. color temperature and saturation;
6. edge sharpness, depth blur, grain, and texture;
7. contact shadow or shared atmospheric layer where physically justified.

Do not use glow as a universal edge repair. Remove color contamination from the mask edge, reconstruct missing edge color, or place the subject in a believable atmosphere.

For stylized skylines, use repeated material/contrast rules and controlled overlap. Do not mix photoreal buildings, flat icons, and unrelated 3D renders without an explicit unifying treatment.

## 5. Raster-to-vector decisions

Vectorize when the source is geometric, flat, and must scale or be recolored. Keep raster when it contains subtle texture, lighting, transparency, or photographic detail.

After Image Trace:

- compare silhouette and important negative spaces with the raster;
- reduce excessive anchor points without changing character;
- remove background shapes and tiny noise;
- inspect compound paths and holes;
- test at final physical size;
- retain the raster source for reference.

Do not call an automatic trace "the original vector."

## 6. Resolution and enlargement

Calculate effective PPI at placed size. Do not trust only embedded DPI metadata.

Use higher PPI for close viewing, fine texture, and small type baked into raster. Large distant backdrops may tolerate lower PPI, but the printer and viewing distance decide the threshold. Keep official logos and type vector whenever possible.

Upscaling cannot recover exact factual detail. Use it for edge continuity and texture, then inspect 100% crops. Regenerate decorative material at a better composition/resolution when enlargement artifacts become the design.

## 7. Image QA

- source is approved/licensed and not a preview thumbnail;
- crop supports the composition and does not amputate awkwardly;
- cutout retains pale, thin, transparent, and internal details;
- perspective and light agree across sources;
- color grade belongs to the brand system;
- no pseudo-text, watermark, model artifact, duplicated element, or impossible geometry remains;
- effective PPI is adequate at placed size;
- masks and retouching have been checked on the final background and at 100%.
