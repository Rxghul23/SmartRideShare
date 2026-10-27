# SmartRideShare

A working corporate ride-sharing application built from both supplied project PDFs. Java owns authentication, ride workflows, administration, and MySQL persistence. Python provides scikit-learn recommendations and demand forecasts. The responsive frontend uses JSP, HTML, CSS, and JavaScript.

## Run on this computer

The dependencies, database, demo accounts, and compiled application are already prepared in `Z:\CAO-DA`.

1. Double-click **START-SMARTRIDE.cmd**.
2. Open **http://localhost:8080/smartride/**. If localhost is slow, use **http://127.0.0.1:8080/smartride/**.
3. Open **LOCAL-LOGIN.txt** for the generated demo password. Sign in as `admin@smartride.local`, `aarav@smartride.local`, or `priya@smartride.local`.
4. Use **STOP-SMARTRIDE.cmd** to stop this project's services.

The existing MySQL80 Windows service remains separate. This project's MySQL runs on **3307**, Tomcat on **8080**, and Python on **5001**, bound to the local computer. The launcher uses the bundled JDK because the pre-existing system Java command is broken.

## Included functionality

- Employee registration, password login, logout, sessions, and administrator access controls.
- Ride offers with seats, timing, preferences, an interactive map, and server-calculated road distance and fare.
- Automatic AI previews when journey details change, saved requests, and ranked matches that refresh every five seconds while the relevant page is visible.
- Transactional bookings, cancellation, final-seat concurrency protection, and ride completion.
- Driver passenger lists with work email for pickup coordination.
- Post-ride ratings, comments, and automatic feedback model retraining.
- Dashboards with ridership trends, shared distance, seat utilisation, estimated savings, and estimated emissions avoided.
- Administrator account controls, ride cancellation, matching/impact settings, system health, audit history, model retraining, and CSV export.
- Seven-day demand forecast with an explicit insufficient-history state.
- Responsive layouts, empty states, form validation, error messages, and accessible labelled controls.

## Use in Eclipse IDE

See **docs/ECLIPSE-SETUP.md** for exact import and run instructions. This is a Maven WAR project with Eclipse `.project`, `.classpath`, and Build/Start launch configurations. Eclipse itself was not installed or launched during implementation.

## Project layout

| Path | Purpose |
| --- | --- |
| `src/main/java/com/smartride` | Java API servlet, JDBC database access, password hashing, Python client |
| `src/main/webapp` | JSP entry page, CSS, browser JavaScript, servlet configuration |
| `src/test/java` | Java security and validation tests |
| `ml-service` | Python matching, training, forecasting, unit tests, dependency pins |
| `database/schema.sql` | Base MySQL database and eight application tables; additive migrations bring the total to eleven |
| `scripts` | Setup, build, start/stop, seeding, integration and browser checks |
| `docs` | Requirements mapping, Eclipse guide, test results, screenshots, complete extracted PDF text |
| `target/smartride.war` | Built Tomcat application |
| `.tools` | Project-local runtimes, Python libraries, Maven cache, and MySQL data |
| `.local-config.json` | Generated local secrets; excluded from source control |
| `LOCAL-LOGIN.txt` | Generated demo credentials; excluded from source control |
| `tmp` | Runtime logs and temporary build/review files |

## Build and validate

In PowerShell from the project folder:

```powershell
.\scripts\build.ps1
.\scripts\start.ps1
. .\scripts\env.ps1
python .\ml-service\test_app.py
python .\scripts\integration_test.py
python .\scripts\browser_check.py
```

The build runs Java tests and deploys the WAR. Tomcat detects a new WAR automatically; allow a few seconds and sign in again after rebuilding. The integration suite creates and removes its own test accounts and rides. Its completion test changes only its test ride's departure time. It expects the supplied demo dataset for the forecast/retraining assertions. The browser check uses the locally installed Google Chrome and the Playwright package; install `playwright` into `.tools/python` if recreating the environment.

The tested local environment uses Microsoft JDK 21.0.8 (Java 17 source target), Tomcat 10.1.44, Maven 3.9.11, MySQL Server 8.0.46, and Python 3.11. Python package versions are pinned in `ml-service/requirements.txt`.

## Data and model notes

The initial 28 days of history, employee profiles, feedback, and upcoming rides are **synthetic demonstration data**. New actions persist in MySQL. A similarity-based cold-start ranker uses scikit-learn cosine similarity plus weighted feature magnitude. After 10 valid rated matched bookings, a random forest trained on feedback contributes 40% of the ranking. Every eligible feedback submission triggers retraining; the model is saved locally. Match features, score, and model version are recorded in MySQL.

The map uses Leaflet and OpenStreetMap tiles. Java calls OSRM to calculate a driving route, distance, and estimated duration, with a bounded 10-minute cache. Fare is INR 5 per routed kilometre per seat, rounded to the nearest rupee. Both values are recalculated and validated on the server when publishing. Failed routing clears stale values and blocks publication until retry succeeds. Preset locations, map clicks, draggable markers, custom coordinates, and browser geolocation are supported. Internet is required for tiles and road routing. ETA excludes live traffic. AI compatibility still compares endpoint proximity, timing, preferences, and feedback; it does not compare full road-path overlap.

The demand model uses weekday/hour features and includes zero-demand hours. It requires at least 14 days of history and produces exploratory estimates. The demo model has not been validated on real employee data; no accuracy claim is made.

Impact calculations use completed rides only, configurable assumptions, and passenger kilometres. They assume a passenger replaces one solo vehicle trip and exclude detours. The Analytics page displays the formulas. Employee metrics cover all passengers in the shared rides the employee participated in; organisation totals count each ride once.

## Scope

This completes the web prototype described in the PDFs. Map-based road routing is now included. Continuous GPS tracking, native mobile apps, voice assistants, EV incentives, and deep learning remain outside this implementation. A local demo payment simulator now records checkout outcomes and simulated refunds; it does not connect to Razorpay or move money. Employee emails are not verified by a corporate identity provider.

For a separate installation, run `scripts/setup.ps1` after installing Python 3.11 and MySQL Server 8.0. It downloads the pinned tools, installs Python packages, creates a separate database, builds, and starts the app. The current scripts target Windows and the MySQL installation path shown above. All application times are Asia/Kolkata.

See **docs/PROJECT-GUIDE.md** for architecture, schema relationships, API routes, and the requirement-to-implementation mapping.

## Map and automatic-matching update (24 September 2026)

The sign-in page shows Ride, Analytics and Admin modules and lets you select the module to open. Admin access is still enforced by Java. Overview includes module shortcuts. The AI matches page tracks your next 20 open future requests while you are viewing it. Automatic matching recommends compatible rides; it never silently reserves a seat. New offers, cancellations and seat changes are reflected on the active matching screen within the next five-second refresh. Background tabs pause polling. The Admin page polls service health while retaining unsaved settings.

JavaScript/CSS assets now have versioned URLs and revalidation headers. Reload any already-open tab to load this release. Historical or past-dated rides do not appear as current matches; create a new offer and request with overlapping future departure times to demonstrate matching.

Run `python scripts/map_realtime_test.py` after loading `scripts/env.ps1` to test map routing, automatic matching across two accounts, saved fares, outage/retry handling, and module sign-in. It uses isolated test accounts and removes their records afterwards. Results: `docs/MAP-TEST-RESULTS.txt`.

The default OSRM endpoint and OpenStreetMap tiles are public community services without a project-specific availability guarantee. Set the server environment variable `ROUTING_URL` to a compatible OSRM service for another deployment. The current fare rate is defined in `Routing.java`. Selected coordinates are sent to the routing service; map tiles are requested by the browser. Names, passwords and feedback are not sent to either map provider.

References: [Leaflet documentation](https://leafletjs.com/reference.html), [OSRM route API](https://project-osrm.org/docs/v5.24.0/api/), [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

Matching diagnostics: zero-result screens now explain whether there are no future offers, only your own offers, no available unbooked seats, a departure-time mismatch, or a route-distance mismatch. Driver offers and passenger requests must belong to different employee accounts. Changing a typed location label does not geocode it; use the map to move the point.



## Chat, demo payments and report (22 October 2026)

- Ride chat supports participant-only conversations, unread counts, persistent history, three-second polling and retry-safe messages. Cancelled passengers lose access; closed rides are read-only.
- My journeys includes Demo payment. Test successful, failed and cancelled attempts; download a demo receipt. Cancelling a paid booking or ride records a simulated refund. No payment API keys, bank details or actual charges are involved.
- Startup applies additive migrations `002_ride_chat.sql` and `003_demo_payments.sql` without resetting existing accounts or rides.
- Verification: 59 automated checks (3 Java, 6 Python, 17 integration, 12 map/matching, 11 chat, 10 payment), plus browser/mobile rendering checks. The map suite passed after retrying a temporary external routing timeout.
- Run `python scripts/chat_test.py` and `python scripts/payment_test.py` after loading `scripts/env.ps1` to repeat the isolated feature checks.
- Final academic report: `output/pdf/Smart_RideShare_Project_Report.pdf` (15 pages, matched to the supplied reference format).
- Teacher explanation, demonstration steps and viva answers: `docs/TEACHER-EXPLANATION.md`.
