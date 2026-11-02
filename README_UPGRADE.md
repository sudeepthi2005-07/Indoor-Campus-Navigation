# Seven-floor indoor campus navigator

This is an upgrade of the supplied Flask/NetworkX/HTML project, retaining its original localization, routing and navigation modules. Building geometry is illustrative, NOT verified VIT architecture.

## Windows 11 / VS Code (PowerShell)
```powershell
cd PATH\TO\campus_upgrade
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. From another terminal with cloudflared installed: `cloudflared tunnel --url http://localhost:5000`. Open the generated HTTPS URL on the phone. Do not share it publicly.

Run tests: `python -m pytest -q`.

The legacy sample building remains in data/ and can be loaded by setting UINS_CAMPUS_DATA. The new default contains seven floors and 224 searchable rooms.

## Limitations
- The building is a synthetic, dimensioned 2D graph, not a surveyed architectural drawing. Room rectangles and doors are schematic.
- Wi-Fi fingerprinting and QR localization require deployed survey/landmarks; browser motion sensors cannot establish trustworthy absolute position.
- Closures are global in-process demo state, not durable across server restarts.
- A* uses a conservative zero heuristic to guarantee correct results with cross-floor lift shortcuts.
- A publicly accessible Cloudflare quick tunnel is for demonstrations, not production authentication.
