# Duty Planner v5 — clock-based user interface

This version retains the v4 OR-Tools solver and its integer-hour relative-time representation, but changes the user-facing schedule start, availability and previous-duty history to actual calendar dates and whole clock hours.

## What's new
- Set a start date and a whole-hour start time (00:00–23:00).
- Enter soldier availability as one or more lines in the format `YYYY-MM-DD HH:00 | YYYY-MM-DD HH:00`.
- Enter previous shifts using actual date/time in the editable history table or CSV/XLSX import.
- View actual start/end date and time in the roster and Excel; PDF axis includes calendar dates.
- Older scenario JSON files with relative hours are supported. When loading a legacy file, the app uses today's date and preserves its original clock hour and relative availability/history.
- The solver still treats nighttime as 00:00–06:00, and Carmel departures as clock hours.

## Notes
- All times are whole hours in the planning location's local clock. No time zone conversion is applied.
- Change the start date/time **before** editing soldier availability and previous duty records.
- Existing relative JSON data are kept internally; the UI translates them. When moving the start date, existing windows shift in calendar time with the plan.
- In the default example, Carmel departures are now correctly specified as clock hours `6,18` (instead of `0,12`). Existing saved JSON values are preserved unchanged; review Carmel departure settings when loading old scenarios.
- Previous-duty records must end at or before the planning start.
- Streamlit's data editor supports pasting date/time text into cells; multiple availability intervals are separated by newlines.

## Deploy
Extract ZIP and upload its contents (not the ZIP) to the `main` branch at the repository root. Streamlit Cloud uses `app.py`. Install packages from `requirements.txt`.

## Validation
Python syntax and standalone time conversion tests passed. Full Streamlit + OR-Tools integration was not run in this environment; review and validate solver outputs before operational use.
