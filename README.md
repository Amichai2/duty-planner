# Duty Planner v3

Streamlit application for personnel roster optimization using OR-Tools CP-SAT.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Changes in v3

- Downloadable landscape timeline PDF (teal Carmel, orange patrol, purple gate) generated from the solved roster.
- Configurable soft target of 16 hours between patrol shifts, including a per-person violation count.
- Variable Carmel team mode: four assigned soldiers always from the same team at each hour; soft share target proportional to available eligible soldier-hours, excluding the driver.
- Carmel allocation comparison displayed on dashboard.

## Notes

- This is a planning tool. Review the roster manually and confirm suitability before use.
- CP-SAT status `FEASIBLE` does not mean proven optimal.
- Availability intervals are relative to the beginning of the planning horizon.
- The driver is permanently reserved for Carmel and cannot be assigned to gate in this version.
- The 16-hour patrol rest and Carmel share are **soft preferences**. Strict no-overlap and minimum rest rules remain hard constraints.
- Solver and Streamlit integration tests require OR-Tools and Streamlit to be installed; they were not available in the packaging environment.
