# Duty Planner v4 — dashboard fix

1. Extract the ZIP locally.
2. Upload **app.py, solver.py, timeline_pdf.py, requirements.txt** and the remaining files to the **root** of GitHub branch `main` (not a nested folder).
3. Commit changes and restart Streamlit.
4. Verify the dashboard renders employment rates.

Fix: the dashboard now recomputes `אחוז תעסוקה` from `פעילות בפועל (שעות)` and `זמינות (שעות)`, and shows a clear message when the deployed solver is outdated.
