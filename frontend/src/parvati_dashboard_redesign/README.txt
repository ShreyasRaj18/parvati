# PARVATI dashboard redesign

This package contains the redesigned React dashboard shell and stylesheet.

## Files
- `App.jsx` — replacement for your current `src/App.jsx`
- `App.css` — replacement for your current `src/App.css`

## Apply
1. Make a backup of your existing `src/App.jsx` and `src/App.css`.
2. Replace those two files with the versions in this package.
3. Keep your existing component files and data assets in place:
   - `src/components/TerrainViewer.jsx`
   - `src/components/BaraShigriMonitor.jsx`
   - `src/components/BaraShigri3DViewer.jsx`
   - their existing CSS files
   - the existing `/public/data/...` assets used by those viewers
4. Run your existing development command (for example `npm run dev`).

No new npm packages are required. The redesign uses the existing `lucide-react`, React, and React Three Fiber components.

## What changed
- Rebranded the interface as PARVATI.
- Added a responsive sidebar and modern dark geospatial workspace.
- Made the Samudra Tapu 3D terrain viewer central to the overview.
- Preserved the existing 3D terrain, NISAR glacier monitoring, and Bara Shigri 3D viewers.
- Added a dedicated Predictive Analysis page with the actual geographic holdout metrics, confusion matrix, top-K screening results and feature importance from the completed model run.
- Added dedicated lake monitoring and scenario explorer pages.
- Clearly labels the supervised model as experimental and weak-discrimination; scores are not calibrated GLOF probabilities.
- Does not modify the dashboard's underlying data or claim hydraulic simulation / live monitoring.


FULL-SCREEN 3D MAP
A Full screen control is overlaid on the 3D terrain map. Click it to expand the map to the entire screen. Click “Exit full screen” or press Esc to return to the dashboard. The browser Fullscreen API is used; it requires a user click and a supported browser.
