# Solid and evolving objects

Choose **Solid / 4D object** beside the plot's PCA controls. It opens an independent window with a snapshot of all analyzed paragraphs that have finite coordinates. The main scatter plot, playback, filters, emotional scores and idiom annotations are unchanged. Reopen the object window to capture newer results. No API calls are made.

## Construction options

- **Outermost points:** the convex hull of the unique points. It encloses all eligible points and fills gaps between clusters.
- **Spatial neighbors:** tetrahedralize the points with 3D Delaunay geometry and retain tetrahedra whose longest edge is no greater than the chosen edge limit. The exterior triangles form the displayed surface. A smaller limit preserves local clusters and can leave cavities, disconnected components or no solid. These are spatial neighbors, not text-order neighbors. Nonmanifold contacts can occur.
- **Text-order tube:** sweep polygonal circular rings along consecutive paragraph positions and cap each connected run. The size control is the tube radius. Missing/unknown paragraph coordinates break the path. Duplicate centers are skipped within runs. Thickness is a visualization choice. Tight bends, reversals and crossings can self-intersect, so no enclosed volume is claimed for tubes.

The edge/radius control does not affect the convex hull. Change its value and press **Apply**. Lengths are in plot-coordinate units. Tube rings have 12 sides. Exported faces are indexed triangles with outward orientation for hulls and retained tetrahedral boundaries.

**Emotion axes** use `(valence, direction, 2*intensity - 1)`, exactly as the main 3D plot. **PCA 3D** uses the same standardized PCA implementation, fitted once to the complete analysis snapshot. Scores are divided by the global plot scale. The frame sequence uses a fixed basis and a fixed display scale so changes in the shape reflect changing samples rather than changing axes. Missing direction is not imputed. Coplanar or collinear data do not define a 3D hull; the source points are shown with an explanation.

Drag to rotate, scroll to zoom, or enable wireframe/source points. A surface exceeding 15,000 triangles is not drawn interactively; choose a shorter moving window or export the complete geometry. Data are not silently sampled.

## The fourth dimension

The fourth coordinate is normalized paragraph order, `tau_i = (i-1)/(N-1)`. For one paragraph it is zero. **Cumulative** uses all eligible paragraphs up to `i`; **Moving window** uses paragraph positions `max(1, i-w+1)` through `i`. Missing paragraphs still occupy positions in this timeline. Scrub the slider or use **Play evolution** to see the 3D slices. Playback advances one paragraph at a time and waits for geometry to finish; it is not a real-time measure of reading speed.

The exported 4D occupied set is defined by the piecewise-constant slices:

`W = union_{i=1}^{N-1} S_i × [tau_i, tau_(i+1))`, plus the final slice at `tau_N` (zero for N=1, otherwise one).

This is an evolving 3D solid in a fourth (text-order) dimension, not a projection of a 4D convex hull. Mesh topology can change between slices. The implementation does not interpolate unmatched vertices. For hulls and tetrahedral unions, the mathematical hypervolume is `sum_i volume(S_i)/(N-1)` over the intervals. Lower-dimensional slices contribute zero. Tube hypervolume is not reported. For N=1, there is no time interval and hypervolume is zero.

## Exports

- **Mesh (.obj):** the current slice's full vertex and triangle arrays, in the chosen coordinate units. Empty surfaces cannot be exported as a mesh. Some OBJ viewers may need backface culling disabled for self-intersecting tube meshes.
- **Description (.txt):** construction equations, coordinate mapping, timeline/window definition, size setting, surface area, volume where meaningful, and geometry limitations.
- **Geometry (.json):** current mesh, source paragraph IDs/coordinates, fixed PCA transform when used, analysis snapshot, parameters and mathematical description. Convex hulls include plane inequalities `n·x+b <= 0`; neighbor envelopes include retained tetrahedra.
- **Evolution (.json):** defaults to Compact: every paragraph time, all source coordinates/emotional results, and the reconstruction recipe, without calculating meshes. Optional Sampled meshes adds geometry at up to 60 evenly spaced frames including the endpoints. Both retain the complete emotional evolution. Select Cumulative or Moving window first. Cancel export or close the object window to cancel. Existing files are replaced only after a completed export.

Current-slice JSON format: `emotional-atlas-object-v1`. Evolution exports from v0.7.5 use `emotional-atlas-evolution-v2`; frame meshes are optional and the representation/mesh_paragraphs fields specify which were computed. JSON face/tetrahedron indices are zero-based; OBJ face indices are one-based. Mesh vertices may include interior/unused input vertices. The original paragraph mapping is retained separately because duplicate positions merge for hull/tetrahedral calculations.

Area and volume describe the chosen geometric construction. They are not validated psychological measurements. The edge-incidence check identifies open/nonmanifold edges but is not a self-intersection or complete manifold test. The neighborhood method can yield multiple solids and vertex/edge contacts; inspect any export before fabrication.

## Verification

Unit fixtures check a cube (volume 8, area 24), a unit tetrahedron (volume 1/6), outward face orientation, separated clusters, edge thresholds, duplicate/coplanar inputs, tube caps, missing paragraphs and moving windows. Native smoke checks cover the separate window, rendering, PCA, evolution settings, and OBJ/TXT/JSON exports. SciPy supplies ConvexHull and Delaunay; NumPy supplies vector and matrix operations. Both are pinned in `requirements.txt`.

## Curved surfaces and color

Choose **Surface finish → Curved · 1 / 2 / 3** to apply one, two or three
Loop subdivision steps to any closed manifold control mesh. Every triangle is
replaced by four; edge and original vertices move by weighted neighbor averages.
This produces a tessellated approximation to a curved limit surface, not merely
a lighting effect. It rounds and generally shrinks the shape; a smoothed hull
may no longer contain every original point. Source scores remain unchanged.
Nonmanifold surfaces are rejected with an explanation. More than 120,000 refined
triangles is rejected; the existing 15,000-triangle interactive display limit applies.

**Surface color…** chooses one color for the entire object. Lighting varies its
brightness to show depth. Wireframe uses the same chosen color. Curvature and color
apply to static and evolving views and are recorded in JSON/TXT exports. OBJ export
writes an accompanying `.mtl` material file; keep the two files together.

For valence n, original vertices update as `(1-n*beta)*v + beta*sum(neighbors)`,
where beta is 3/16 for n=3 and 3/(8n) otherwise. An edge with endpoints a,b and
opposite vertices c,d gets `3/8*(a+b)+1/8*(c+d)`. See the
[PBRT subdivision discussion](https://www.pbr-book.org/3ed-2018/Shapes/Subdivision_Surfaces).
Area and volume are recalculated from the refined triangles, not from the old hull.
They approximate the curved surface; tube volumes remain unreported. Control hull
inequalities and tetrahedra are explicitly labeled as control geometry in JSON.

Object axes are visible by default and can be toggled with **Axes**. They rotate with the object and keep fixed bounds across frames. Emotional coordinates label X as valence, Y as direction and Z as `2 × intensity − 1`; ticks show these plot-coordinate values. PCA labels use PC1/PC2/PC3 divided by the fixed global scale. The fourth coordinate is labeled **Time τ** beside the paragraph slider. Axes are viewing guides, not geometry added to the exported mesh.

### Export resource limits (v0.7.5)

Compact evolution exports never rebuild geometry. They contain every paragraph's
time plus the complete source coordinates, emotional analysis and construction
parameters needed to reconstruct all shapes. Hypervolume is null because it is not
computed. Sampled mesh exports retain at most one calculated mesh at a time and
include at most 60 meshes, at most 1,500 source points per sampled frame, at most
20,000 triangles per frame and 250,000 triangles overall. Exceeding these limits
stops the export with an explanation and leaves an existing destination unchanged.
The compact option remains available without these geometry limits.

Cancel is checked while writing, between frames, and during subdivision loops.
A native triangulation already in progress must finish before cancellation takes
effect. Exports pause animation to avoid competing geometry workloads.
