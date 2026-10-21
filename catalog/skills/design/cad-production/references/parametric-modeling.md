# Parametric modeling

Define units, origin, primary datums, named parameters, and external interfaces first. Keep dimensions tied to requirements or source references, not anonymous numeric literals.

Build stable feature groups: base envelope, primary interfaces, cuts/openings, repeated features, rounds/chamfers, and derived patterns. Prefer constraints and named selections that survive ordinary dimension changes. Recompute and inspect after each group.

For assemblies, identify fixed components, mates/constraints, degrees of freedom, clearance states, service/removal paths, and a bill of materials. Separate purchased components from fabricated parts. Never invent a supplier part from an approximate mesh when an official STEP model or datasheet can be sourced.

Record deviations between design intent, visible/render dimensions, and production dimensions. Keep preliminary geometry clearly marked until an owner approves it.
