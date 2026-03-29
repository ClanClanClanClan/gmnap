
# GMNAP V7 — Push 2 (Stage 2 DetectRegion + Stage 3 RegionHooks baseline)

Adds:
- Region detector (script-based baseline) and minimal A1/E1 region hooks.
- Pipeline wiring patch to insert Stage 2 and Stage 3 before later stages.
- Tests that verify A1 cleanup ("Family, Given") and E1 pass-through.

Spec alignment: Stage 2 uses script cues + overlays; Stage 3 runs clean→augment→validate; richer rules remain for later pushes.