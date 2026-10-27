"""Build the professor's product-development submission without local secrets."""
from pathlib import Path
import shutil,zipfile,hashlib,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/submission';BASE.mkdir(parents=True,exist_ok=True)
NAME='SmartRideShare_DA3_26MAI1021_26MCB1023';STAGE=BASE/NAME
if STAGE.exists():raise SystemExit('Submission folder already exists; use a new revision rather than overwrite it.')
for folder in ['01_Review_3_PPT','02_Final_Project_Report','03_Demo','04_Project_Code']: (STAGE/folder).mkdir(parents=True)
assets=ROOT/'output/submission_assets';code=STAGE/'04_Project_Code/SmartRideShare';code.mkdir()
shutil.copy2(assets/'SmartRideShare_Review_3.pptx',STAGE/'01_Review_3_PPT')
shutil.copy2(ROOT/'output/pdf/Smart_RideShare_Project_Report.pdf',STAGE/'02_Final_Project_Report')
for name in ['SmartRideShare_Demo.mp4','Demo_Chapters.txt']:shutil.copy2(assets/name,STAGE/'03_Demo')
for folder in ['src','database']:
 shutil.copytree(ROOT/folder,code/folder)
for name in ['pom.xml','.project','.classpath','.gitignore','SmartRide Build.launch','SmartRide Start.launch','START-SMARTRIDE.cmd','STOP-SMARTRIDE.cmd']:shutil.copy2(ROOT/name,code/name)
(code/'ml-service').mkdir()
for name in ['app.py','test_app.py','requirements.txt']:shutil.copy2(ROOT/'ml-service'/name,code/'ml-service'/name)
(code/'scripts').mkdir()
for p in (ROOT/'scripts').iterdir():
 if p.suffix not in ['.py','.ps1'] or p.name in ['package_submission.py','create_report.py','record_submission_demo.py']:continue
 content=p.read_text(encoding='utf-8-sig').replace("pathlib.Path(r'Z:\\CAO-DA')","pathlib.Path(__file__).resolve().parents[1]")
 (code/'scripts'/p.name).write_text(content,encoding='utf-8')
(code/'docs').mkdir();(code/'docs/screenshots').mkdir()
for name in ['PROJECT-GUIDE.md','ECLIPSE-SETUP.md','TEACHER-EXPLANATION.md','TEST-RESULTS.txt','MAP-TEST-RESULTS.txt','CHAT-TEST-RESULTS.txt','PAYMENT-TEST-RESULTS.txt']:
 content=(ROOT/'docs'/name).read_text(encoding='utf-8-sig').replace('Z:\\CAO-DA','C:\\SmartRideShare').replace('Z:\\eclipse-workspace','C:\\eclipse-workspace');(code/'docs'/name).write_text(content,encoding='utf-8')
(code/'requirements-validation.txt').write_text('playwright==1.62.0\n',encoding='utf-8')
readme='''SMART RIDESHARE - DIGITAL ASSIGNMENT III
Product development submission | Review 3
Godwin Durai Raja A (26MAI1021) - M.Tech CSE (AI and ML)
Raghul T (26MCB1023) - M.Tech Big Data Analytics
VIT Chennai | Packaged 24 October 2026

PROFESSOR'S REQUIREMENT -> INCLUDED FILE
1. PPT for Review-3 -> 01_Review_3_PPT/SmartRideShare_Review_3.pptx
2. Final research paper (for Research project) -> Not applicable: this submission is a product-development project.
3. Final project report (for Product development) -> 02_Final_Project_Report/Smart_RideShare_Project_Report.pdf
4. Demo (both tracks) -> 03_Demo/SmartRideShare_Demo.mp4 and Demo_Chapters.txt
5. Code with execution procedure -> 04_Project_Code/SmartRideShare and EXECUTION_PROCEDURE.txt

The 14-slide PPTX is editable. The final report has 15 pages.
The captioned walkthrough uses actual application screens. It has no audio.
Payment operates in test mode without money movement or payment API keys.
Maps use internet-based road routing and map tiles. Seed history is synthetic.

Start with the PPT, report and MP4. For a live run, follow EXECUTION_PROCEDURE.txt.
Local passwords, database files, installed tools and machine-specific configuration are deliberately excluded. Setup generates new local credentials.
SHA256SUMS.txt lists every submitted file for integrity verification.
'''
(STAGE/'READ_ME_FIRST.txt').write_text(readme,encoding='utf-8')
execution='''SMART RIDESHARE - EXECUTION PROCEDURE

A. PREREQUISITES (Windows x64)
1. Python 3.11 installed and available as python on PATH.
2. MySQL Server 8.0 binaries at C:\\Program Files\\MySQL\\MySQL Server 8.0.
   The scripts create a separate local database instance on port 3307.
   If MySQL is installed elsewhere, change mysqlBase in scripts/setup.ps1 and the mysqld.exe path in scripts/start.ps1.
3. Internet access for first setup (Java, Maven, Tomcat and Python dependencies), map tiles and OSRM road routes.
4. Free local ports 3307 (MySQL), 5001 (Python), 8080 and 8005 (Tomcat).
5. Optional: Eclipse IDE for Enterprise Java and Web Developers; Chrome for browser tests.

B. FIRST RUN
1. Extract the ZIP. Copy the complete 04_Project_Code/SmartRideShare folder to C:\\SmartRideShare.
   Use a short path without spaces because the supplied Windows process-launch scripts assume this.
2. Open PowerShell in C:\\SmartRideShare.
3. Run:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\setup.ps1
4. Setup downloads the pinned JDK, Maven and Tomcat into .tools, installs Python packages, builds the WAR, starts a dedicated MySQL instance, seeds the sample records and applies all three SQL files.
5. Wait for: SmartRide is running.
6. Open http://localhost:8080/smartride/ (or http://127.0.0.1:8080/smartride/).
7. Open the newly generated LOCAL-LOGIN.txt for the local password. Example accounts:
   admin@smartride.local (administrator)
   aarav@smartride.local (employee)
   priya@smartride.local (employee / driver)
   These credentials are generated per installation, not shipped in the ZIP.

C. SUBSEQUENT RUNS / STOP
Double-click START-SMARTRIDE.cmd to run the project.
Double-click STOP-SMARTRIDE.cmd to stop only this project's services.
Do not delete .local-config.json after initialisation; it contains the credentials for that local database instance.

D. CLASSROOM WALKTHROUGH
1. Use separate normal and incognito browser sessions for two different employee accounts.
2. Driver: offer Velachery -> Tidel Park, tomorrow 09:00, two passenger seats. Wait for route and price calculation before publishing.
3. Passenger: request the same route and time. Save the request and open AI matches.
4. The driver's offer should appear on the next active five-second refresh. Book a seat.
5. My journeys -> Payment -> Pay now. Test mode records the payment without charging money; download the receipt.
6. Open Ride chat in both accounts and exchange a pickup message.
7. Cancel the passenger booking to demonstrate seat restoration and the test refund.
8. Open Analytics, then use the administrator account for user management, service health and CSV reports.
9. Completion is allowed only after departure; a completed booking accepts one feedback submission.
Old seeded offers may be in the past. Create a fresh future ride for the demonstration. A user cannot book their own ride.

E. ECLIPSE
After setup, import C:\\SmartRideShare as an Existing Maven Project.
Use .tools\\jdk-21.0.8+9 as the JDK (source target Java 17).
The project name must be SmartRideShare for the supplied launch configurations.
Run SmartRide Build.launch / SmartRide Start.launch as External Tools.
See docs/ECLIPSE-SETUP.md for the full procedure. Do not run a second Tomcat on the same port.

F. TESTS
In PowerShell from the project directory:
  . .\\scripts\\env.ps1
  & .\\scripts\\build.ps1
  Push-Location ml-service
  python -m unittest test_app
  Pop-Location
After Tomcat finishes redeploying and the home page loads:
  python scripts/integration_test.py
Optional browser checks (requires Chrome at its standard Windows path):
  python -m pip install --target .tools/python -r requirements-validation.txt
  python scripts/map_realtime_test.py
  python scripts/chat_test.py
  python scripts/payment_test.py
Existing evidence records 59 passing automated checks on the development machine. External routing can time out; use Retry route and rerun the affected check. The ZIP is not an offline dependency bundle.

G. TROUBLESHOOTING
Route unavailable: check internet and click Retry route. No stale fare should remain.
No matches: check different accounts, future times, remaining seats and both location coordinates.
Database fails: check MySQL installation path and port 3307; read tmp/mysql-error.log.
App unavailable: read tmp/tomcat-error.log and tmp/ml-error.log.
404 immediately after build: allow Tomcat to complete WAR redeployment, then refresh.
The demo video and report can be reviewed without installing or running the application.
'''
(STAGE/'04_Project_Code/EXECUTION_PROCEDURE.txt').write_text(execution,encoding='utf-8');(code/'README.md').write_text('# Smart RideShare\n\n'+execution,encoding='utf-8')
files=sorted(p for p in STAGE.rglob('*') if p.is_file())
(STAGE/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(STAGE).as_posix() for p in files)+'\n',encoding='utf-8')
zip_path=BASE/(NAME+'.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(STAGE.rglob('*')):
  if p.is_file():z.write(p,NAME+'/'+p.relative_to(STAGE).as_posix())
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 assert not any('/.tools/' in n or '/.local-config.json' in n or n.endswith('/LOCAL-LOGIN.txt') or '__pycache__' in n for n in z.namelist())
 config=json.loads((ROOT/'.local-config.json').read_text())
 for n in z.namelist():
  if n.endswith(('.java','.py','.ps1','.md','.txt','.json','.xml','.jsp','.js','.sql','.launch','.cmd')):
   data=z.read(n)
   assert all(str(secret).encode() not in data for secret in config.values()),'Local secret found in '+n
print(json.dumps({'zip':str(zip_path),'bytes':zip_path.stat().st_size,'files':len(files)+1,'integrity':'passed','secrets_check':'passed'},indent=2))
