# Duty Planner v4

Adds partial historical duties (CSV/Excel/manual) and active-duty utilization metrics to v3. History records use relative hours ending at or before 0 (planning start), e.g. `-8,0`. Known prior patrol/guard records constrain the new plan's minimum rest, soft rest and repeat-night rules; missing history is not treated as confirmed rest. Historical Carmel entries are definition-only and do not imply actual departures.

Active hours = patrol hours + guard hours + Carmel exit hours (including driver). Utilization = active hours / availability hours. Dashboard reports per-person average and weighted overall rate.

## Run
`pip install -r requirements.txt`
`streamlit run app.py`

## Private access
Use Streamlit Community Cloud app settings to set visibility to Private and invite specific email addresses. This is configured in Streamlit, not in this code. Verify access restrictions in your own Cloud account. Never store operationally sensitive rosters in a public repository.

## Limitations
Historical shifts must end at or before time 0. Locking preassigned future shifts is not implemented. Historical Carmel definitions do not encode exits. Tests in this environment were limited to syntax and static inspection because OR-Tools and Streamlit are not installed. The previous engine's constraints and audit coverage require end-to-end validation before operational use.
