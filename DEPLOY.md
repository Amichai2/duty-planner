# Deploy Duty Planner (free tier)

1. Create a GitHub account (if needed) and a new repository. Use anonymous/sample data only; avoid sensitive staffing information on public hosting.
2. Upload `app.py`, `solver.py`, `requirements.txt`, and `.streamlit/config.toml` to the repository root. GitHub web: Add file -> Upload files -> Commit changes.
3. Sign in at https://share.streamlit.io/ with GitHub, select Create app, choose the repository, branch `main`, and main file `app.py`.
4. Deploy. Wait for dependencies to install, then open the resulting URL on your phone.
5. On your phone, use the browser menu -> Add to Home Screen.

The free tier has compute and availability limits. A public URL is not an access-control mechanism. Do not enter operationally sensitive schedules without approved private hosting and access controls.

Local run:
`pip install -r requirements.txt`
`streamlit run app.py`

This is a prototype: syntax verified, but optimization runtime and end-to-end deployment have not been validated here. Review generated schedules before use.
