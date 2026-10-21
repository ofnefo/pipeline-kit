# Raster export and QA

Confirm before export:

- exact pixel dimensions and intended physical size;
- RGB/CMYK mode and embedded profile required by the recipient;
- transparency and premultiplied-edge behavior;
- 8/16-bit requirement, alpha requirement, and file-size limit;
- crop, bleed/wrap, safe area, seams, and effective PPI at final scale;
- whether the recipient needs layered PSD/PSB, TIFF, PNG, JPEG, or a proof only.

Inspect the exported file independently from the working document. Compare dimensions, profile, alpha, visible bounds, spelling, and protected pixels. For print, keep final type and logos vector when possible and route the package to `$design-production-preflight`.
