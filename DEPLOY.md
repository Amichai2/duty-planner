# Update existing GitHub / Streamlit app

1. Unzip this archive locally.
2. Open your repository `Amichai2/duty-planner` on branch `main`.
3. Upload or replace **app.py**, **solver.py**, **timeline_pdf.py**, **requirements.txt**, and **README.md** in the repository root. Do not upload only the ZIP.
4. Commit the changes on `main`.
5. Streamlit Cloud should redeploy. If not, reboot the app and inspect logs.
6. Verify that the PDF download appears in the dashboard after solving and that Carmel team offers the variable mode.

The new `timeline_pdf.py` is required. `requirements.txt` adds matplotlib.
