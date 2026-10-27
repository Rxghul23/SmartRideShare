"""Live map/fare and automatic-match regression test with isolated database fixtures."""
import json,pathlib,uuid
from datetime import datetime,timedelta
import pymysql
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];CFG=json.loads((ROOT/'.local-config.json').read_text());BASE='http://127.0.0.1:8080/smartride/'
ids=[];tag=uuid.uuid4().hex[:8];password='MapTest!2026Secure';checks=[]
def passed(s):checks.append(s);print('PASS',s,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
 driver=browser.new_context();passenger=browser.new_context()
 def call(ctx,path,body=None,expected=200):
  res=ctx.request.get(BASE+'api'+path) if body is None else ctx.request.post(BASE+'api'+path,data=body,headers={'X-CSRF-Token':getattr(ctx,'csrf','')})
  assert res.status==expected,(path,res.status,res.text());return res.json()
 try:
  for i,ctx in enumerate([driver,passenger]):
   email=f'maps-{tag}-{i}@example.test';ids.append(call(ctx,'/register',{'name':'Map QA '+str(i),'email':email,'password':password,'department':'Testing'})['id'])
   ctx.email=email;ctx.csrf=call(ctx,'/login',{'email':email,'password':password})['csrf']
  page=passenger.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE);page.locator('.hero').wait_for();page.locator('nav [data-page=find]').click();page.locator('#find-form').wait_for()
  page.locator('#find-form[data-route-ready="true"]').wait_for(timeout=30000)
  page.locator('#matches .panel').wait_for();assert page.locator('.leaflet-container').count()==1
  assert page.locator('.leaflet-overlay-pane path').count()>0
  initial=call(passenger,'/mine');assert not initial['requests'];passed('Map and automatic AI preview load without creating duplicate requests')
  form=page.locator('#find-form');form.locator('button.primary').click();page.get_by_text('Request saved. AI is watching for compatible rides.',exact=True).wait_for()
  saved=call(passenger,'/mine')['requests'];assert len(saved)==1;req=saved[0]
  trip={k:req[k] for k in ['origin','destination','origin_lat','origin_lng','dest_lat','dest_lng','departure','preference']};trip.update(seats=1,price=1,distance_km=999)
  quote=call(driver,'/route',trip);ride=call(driver,'/rides',trip)['id']
  offer=next(r for r in call(driver,'/mine')['offers'] if r['id']==ride)
  assert offer['price']==quote['price'] and offer['distance_km']==quote['distance_km'];passed('Server recomputes route and fare instead of trusting stale/tampered form values')
  page.locator(f'#matches [data-book="{ride}"]').wait_for(timeout=18000);passed('A newly published ride appears automatically for a saved request')
  feed=call(passenger,'/recommendations');assert any(m['id']==ride for g in feed['groups'] for m in g['recommendations']['matches']);passed('Saved AI recommendations are generated from live MySQL offers')
  page.locator(f'#matches [data-book="{ride}"]').click();page.locator('[data-cancel-booking]').wait_for();passed('Automatically recommended ride can be booked with persisted match history')
  page.locator('nav [data-page=offer]').click();of=page.locator('#offer-form');of.wait_for();page.locator('#offer-form[data-route-ready="true"]').wait_for(timeout=30000)
  first=(of.locator('[name=distance_km]').input_value(),of.locator('[name=price]').input_value())
  of.locator('[name=origin]').select_option('Sholinganallur');of.locator('[name=destination]').select_option('Tambaram')
  page.locator('#offer-form[data-route-ready="true"]').wait_for(timeout=30000)
  second=(of.locator('[name=distance_km]').input_value(),of.locator('[name=price]').input_value());assert first!=second,(first,second);assert int(second[1])==int(float(second[0])*5+0.5)
  assert of.locator('[name=price]').get_attribute('readonly') is not None
  passed('Location changes update road distance and fare: '+str(first)+' -> '+str(second))
  of.locator('[name=destination]').select_option('Sholinganallur');assert of.locator('[name=price]').input_value()=='';assert of.locator('[name=distance_km]').input_value()=='';passed('Identical endpoints clear stale route values')
  of.locator('[name=destination]').select_option('Tambaram');page.locator('#offer-form[data-route-ready="true"]').wait_for(timeout=30000)
  page.screenshot(path=str(ROOT/'docs/screenshots/06-live-map.png'),full_page=True)
  # Simulate routing outage; old fare must not survive or allow publishing.
  page.route('**/api/route',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'error':'Routing unavailable (test)'})))
  of.locator('[name=destination]').select_option('Guindy');page.get_by_text('Routing unavailable (test)',exact=True).wait_for()
  assert of.locator('[name=price]').input_value()=='' and of.locator('[name=distance_km]').input_value()=='';assert page.evaluate("document.querySelector('#offer-form').dataset.routeReady")=='false'
  page.unroute('**/api/route');of.locator('[data-route-retry]').click();page.locator('#offer-form[data-route-ready="true"]').wait_for(timeout=30000);passed('Routing outage clears stale values; retry recovers')
  # Map selection updates form coordinates and triggers routing.
  of.locator('[data-map-mode=destination]').click();of.locator('.route-map').click(position={'x':220,'y':160});assert of.locator('[name=destination]').input_value()=='Custom location'
  page.locator('#offer-form[data-route-ready="true"]').wait_for(timeout=30000);passed('Clicking the map sets coordinates and recalculates the route')
  page.locator('nav [data-page=ai]').click();page.locator('.page-heading').wait_for();page.locator('nav [data-page=offer]').click();of=page.locator('#offer-form');of.wait_for()
  page.set_viewport_size({'width':390,'height':844});page.locator('#offer-form[data-route-ready="true"]').wait_for(timeout=30000);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');passed('Mobile map layout and map navigation lifecycle')
  assert not errors,errors
  call(passenger,'/admin/users',expected=403);passed('Administrator module remains protected')
  auth=browser.new_context();login=auth.new_page();login.goto(BASE);assert login.locator('.auth-modules>div').count()==3
  login.locator('[name=module]').select_option('analytics');login.locator('[name=email]').fill(driver.email);login.locator('[name=password]').fill(password);login.locator('#auth-submit').click();login.get_by_text('Every shared ride adds up.',exact=True).wait_for();passed('Sign-in module selector opens the selected authorised module')
 finally:
  browser.close()
  c=pymysql.connect(host='127.0.0.1',port=3307,user='smartride',password=CFG['dbPassword'],database='smartride',autocommit=True)
  if ids:
   marks=','.join(['%s']*len(ids))
   with c.cursor() as q:
    q.execute(f'DELETE f FROM feedback f JOIN bookings b ON f.booking_id=b.id WHERE b.passenger_id IN ({marks})',ids)
    q.execute(f'DELETE m FROM match_history m JOIN ride_requests r ON m.request_id=r.id WHERE r.user_id IN ({marks})',ids)
    q.execute(f'DELETE FROM bookings WHERE passenger_id IN ({marks})',ids)
    q.execute(f'DELETE FROM ride_requests WHERE user_id IN ({marks})',ids)
    q.execute(f'DELETE FROM rides WHERE driver_id IN ({marks})',ids)
    q.execute(f'DELETE FROM audit_log WHERE user_id IN ({marks})',ids)
    q.execute(f'DELETE FROM users WHERE id IN ({marks})',ids)
  c.close()
(ROOT/'docs/MAP-TEST-RESULTS.txt').write_text(datetime.now().isoformat()+'\n'+'\n'.join('PASS '+s for s in checks)+'\n',encoding='utf-8')
print(len(checks),'map and automatic matching checks passed; isolated fixtures removed.')
