# Upgrade from v4
1. Download and unzip the package.
2. Upload `app.py`, `solver.py`, `timeline_pdf.py`, `requirements.txt`, and README to your GitHub repository's `main` branch root (replace existing files).
3. Wait for Streamlit Cloud to redeploy, then refresh the app.
4. Under **משימות ואילוצים**, choose the calendar date and the whole-hour start time.
5. Under **כוח אדם וזמינות**, edit each availability interval using `YYYY-MM-DD HH:00 | YYYY-MM-DD HH:00` (one interval per line), and save.
6. Under **איושים קודמים**, enter/import real dates and clock times.
7. Check Carmel departures (usually `6,18`), run optimization, and verify the audit and exported PDF.

This update does not include hosting or authentication changes. Existing Streamlit access settings are unaffected.
