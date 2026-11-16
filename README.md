# GlacierPulse UI — corrected raster mapping

## Install
Copy `app` and `requirements-app.txt` into `F:\parvati`.

```powershell
cd F:\parvati
pip install -r requirements-app.txt
streamlit run .\app\app.py
```

The app uses exact filenames supplied from `F:\parvati\outputs\bara_shigri\layer3`.

## Important corrections
- Speed is explicitly read from `bara_shigri_horizontal_magnitude_velocity_m_per_year.tif`.
- Formal speed uncertainty is explicitly read from `bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif`.
- The candidate mask is applied to the movement and quality layers.
- Map axes show projected easting/northing coordinates in metres, not pixel row/column.
- Grid dimensions are checked before applying the mask.
- The app does not claim to predict GLOF timing. Flood-path output requires separate terrain and hydrodynamic modelling.

This app reads but does not modify your scientific output rasters.
