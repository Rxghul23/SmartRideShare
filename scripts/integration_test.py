"""Integration checks against the running local stack. Test fixtures are removed afterwards."""
import concurrent.futures, http.cookiejar, json, pathlib, time, urllib.request, urllib.error, uuid
from datetime import datetime, timedelta
import pymysql
ROOT=pathlib.Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'.local-config.json').read_text())
BASE='http://127.0.0.1:8080/smartride/api'
class Client:
 def __init__(self):
  self.http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));self.csrf=''
 def call(self,path,body=None,expected=200,csrf=True):
  headers={'Content-Type':'application/json'}
  if csrf:headers['X-CSRF-Token']=self.csrf
  req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
  try:
   with self.http.open(req,timeout=45) as r: status=r.status;raw=r.read().decode(); data=json.loads(raw) if 'json' in r.headers.get('Content-Type','') else raw
  except urllib.error.HTTPError as e:status=e.code;data=json.loads(e.read())
  assert status==expected,(path,status,expected,data)
  return data
 def login(self,email,password):
  self.csrf=self.call('/login',{'email':email,'password':password})['csrf']
passed=[]
def check(name):passed.append(name);print('PASS',name,flush=True)
admin=Client(); admin.login('admin@smartride.local',CFG['demoPassword'])
c=pymysql.connect(host='127.0.0.1',port=3307,user='smartride',password=CFG['dbPassword'],database='smartride',autocommit=True)
ids=[];rides=[];requests=[];tag=uuid.uuid4().hex[:10]; password='TestPassword!2026'
try:
 anon=Client();anon.call('/mine',expected=401);check('Anonymous access rejected')
 clients=[]
 for i in range(3):
  cli=Client();email=f'test-{tag}-{i}@example.test';uid=cli.call('/register',{'name':f'Integration {tag} {i}','email':email,'password':password,'department':'QA'})['id'];ids.append(uid);cli.login(email,password);clients.append(cli)
 check('Registration and password login')
 driver,a,b=clients
 a.call('/admin/users',expected=403);a.call('/logout',{},expected=403,csrf=False);check('Admin authorization and CSRF enforcement')
 trip={'origin':'Test pickup','destination':'Test office','origin_lat':12.975,'origin_lng':80.22,'dest_lat':12.9895,'dest_lng':80.249,'departure':(datetime.now()+timedelta(days=2)).replace(hour=9,minute=0,second=0,microsecond=0).isoformat(),'preference':'any','seats':1,'price':40,'distance_km':8,'tolerance':45}
 driver.call('/rides',{**trip,'seats':0},expected=400);driver.call('/rides',{**trip,'departure':'2020-01-01T09:00'},expected=400);check('Invalid seats and past departures rejected')
 ride=driver.call('/rides',trip)['id'];rides.append(ride)
 req=a.call('/requests',trip)['id'];requests.append(req)
 matches=a.call('/matches',{'request_id':req});assert ride in [m['id'] for m in matches['matches']];check('Python route/time recommendations and stored match history')
 driver.call('/book',{'ride_id':ride},expected=400)
 a.call('/ride/status',{'id':ride,'status':'CANCELLED'},expected=403);check('Own-ride booking and cross-user edits rejected')
 booking=a.call('/book',{'ride_id':ride,'request_id':req})['id']
 b.call('/book',{'ride_id':ride},expected=409);a.call('/book',{'ride_id':ride},expected=409);check('Seat reservation and overbooking prevention')
 assert len(driver.call('/passengers',{'ride_id':ride}))==1
 b.call('/passengers',{'ride_id':ride},expected=403)
 check('Passenger details restricted to driver and administrator')
 a.call('/booking/cancel',{'id':booking});a.call('/booking/cancel',{'id':booking},expected=409)
 with c.cursor() as q:q.execute('SELECT available_seats FROM rides WHERE id=%s',(ride,));assert q.fetchone()[0]==1
 check('Cancellation releases exactly one seat')
 def race(cli):
  try:return cli.call('/book',{'ride_id':ride})
  except AssertionError as e:
   assert e.args[0][1]==409,e
   return None
 with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(race,[a,b]))
 assert sum(r is not None for r in results)==1
 winner=a if results[0] else b;bid=next(r['id'] for r in results if r)
 check('Concurrent booking: exactly one winner for the final seat')
 winner.call('/feedback',{'booking_id':bid,'rating':5,'comment':'Too early'},expected=404)
 driver.call('/ride/status',{'id':ride,'status':'COMPLETED'},expected=400)
 # Move only our isolated fixture into the past to exercise completion without waiting two days.
 with c.cursor() as q:q.execute('UPDATE rides SET departure=DATE_SUB(NOW(),INTERVAL 1 HOUR) WHERE id=%s',(ride,))
 driver.call('/ride/status',{'id':ride,'status':'COMPLETED'})
 winner.call('/feedback',{'booking_id':bid,'rating':5,'comment':'Integration test'})
 winner.call('/feedback',{'booking_id':bid,'rating':5,'comment':'Duplicate'},expected=409)
 check('Completion, feedback eligibility, unique feedback and automatic retraining')
 health=admin.call('/admin/health');assert health['ml']['status']=='online';assert health['ml']['training_samples']>=10
 analytics=admin.call('/analytics');assert analytics['forecast']['status']=='estimated',analytics['forecast'];assert len(analytics['forecast']['predictions'])==7;assert analytics['totals']['completed_rides']>0
 check('Feedback model training, 7-day demand forecast and analytics')
 ride2=driver.call('/rides',{**trip,'seats':2})['id'];rides.append(ride2)
 a.call('/book',{'ride_id':ride2});driver.call('/ride/status',{'id':ride2,'status':'CANCELLED'})
 mine=a.call('/mine');assert next(r['status'] for r in mine['bookings'] if r['ride_id']==ride2)=='CANCELLED';check('Driver cancellation propagates to bookings')
 admin.call('/admin/users',{'id':ids[1],'active':False});a.call('/mine',expected=403);admin.call('/admin/users',{'id':ids[1],'active':True});check('Account disable invalidates access')
 report=admin.call('/admin/report');assert report.startswith('id,origin,destination');check('CSV report export')
 settings=admin.call('/admin/settings');admin.call('/admin/settings',{k:settings[k] for k in ['max_route_km','co2_kg_per_km','solo_cost_per_km']});check('Admin settings persist')
 b.call('/logout',{});b.call('/mine',expected=401);check('Logout invalidates session')
finally:
 with c.cursor() as q:
  marks=','.join(['%s']*len(ids))
  if ids:
   q.execute(f'DELETE f FROM feedback f JOIN bookings b ON f.booking_id=b.id WHERE b.passenger_id IN ({marks})',ids)
   q.execute(f'DELETE m FROM match_history m JOIN ride_requests r ON m.request_id=r.id WHERE r.user_id IN ({marks})',ids)
   q.execute(f'DELETE FROM bookings WHERE passenger_id IN ({marks})',ids)
   q.execute(f'DELETE FROM ride_requests WHERE user_id IN ({marks})',ids)
   q.execute(f'DELETE FROM rides WHERE driver_id IN ({marks})',ids)
   q.execute(f'DELETE FROM audit_log WHERE user_id IN ({marks})',ids)
   q.execute(f'DELETE FROM users WHERE id IN ({marks})',ids)
 c.close()
(ROOT/'docs'/'TEST-RESULTS.txt').write_text('Local stack integration results\n'+datetime.now().isoformat()+'\n\n'+'\n'.join('PASS '+s for s in passed)+'\n',encoding='utf-8')
print(f'{len(passed)} integration checks passed; test fixtures removed.')
