# Document conventions: stamps, acts, waybills, closing packets

Defaults that worked in practice for Russian commercial paperwork. A project may override any of them; record the
override in the project config.

## Stamps and signatures

- Use only colour originals supplied by the operator for that organisation; never redraw or synthesise a stamp or a
  signature.
- Round organisation stamps about 45 mm in diameter, the same physical size across the whole package.
- Blend with Multiply so black text under the imprint stays black (no white box, no opaque overlay).
- Pages without stamps and all document text stay byte-identical: overlay onto the page, never re-typeset it.
- A workable toolchain: pypdf for page merging, reportlab for the overlay drawn with Multiply, pdfplumber to measure
  the placed image size, pypdfium2 to render pages for visual QA.
- Placing supplied stamps into the project's own documents can be a standing permission; signing or sending for a
  third party never is.

## Acts

- The date appears once, in the header. Do not repeat the client's ИНН/КПП and the date in the signature block.
- Delivered scope and period match the contract/appendix wording; evidence (photos, reports) is listed, not implied.

## Waybills (ТрН / ТТН)

- Check the current mandatory form before building one. The paper «Транспортная накладная» per ПП РФ №2200
  (приложение 4) applies until the electronic ЭТрН becomes mandatory (announced for 01.09.2026); after that, paper is
  allowed only in the listed exceptions.
- One vehicle per waybill: vehicle, from/to, cargo, volume. A typical event-freight vehicle is a 12 m / 20 t truck.
- Weights are left blank on the form and filled at loading; give the number of places.
- On the form list cargo groups (e.g. light, screen, sound, TV, IT, trusses, cables, other); put the per-item
  inventory with serial numbers into an annex. Items without serials: «б/н по списку …».
- Stamping: signature at «Отпуск разрешил», stamp at «М.П.», and on the last page «Сдал» plus the sender's stamp.

## Payers, cash and closing documents

- Record the payer of every payment; cash is a separate block.
- Each contractor's closing packet for the client report: contract, act and УПД (or invoice + act where УПД is not
  used).
- Contractor accreditation and similar fees are separate lines, not buried in a unit price.
