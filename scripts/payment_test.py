"""Isolated API and two-browser chat regression; removes all fixtures."""
import json,pathlib,uuid
from datetime import datetime
import pymysql
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];CFG=json.loads((ROOT/'.local-config.json').read_text());BASE='http://127.0.0.1:8080/smartride/'
checks=[];ids=[];ride=None;tag=uuid.uuid4().hex[:8]
db=pymysql.connect(host='127.0.0.1',port=3307,user='smartride',password=CFG['dbPassword'],database='smartride',autocommit=True)
def passed(s):checks.append(s);print('PASS '+s,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
 contexts=[browser.new_context(viewport={'width':1440,'height':1000}) for _ in range(3)]
 def call(ctx,path,body=None,status=200):
  r=ctx.request.get(BASE+'api'+path) if body is None else ctx.request.post(BASE+'api'+path,data=body,headers={'X-CSRF-Token':getattr(ctx,'csrf','')})
  assert r.status==status,(path,r.status,r.text());return r.json()
 try:
  for i,ctx in enumerate(contexts):
   email=f'chat-{tag}-{i}@example.test';password='ChatTest!2026';ids.append(call(ctx,'/register',{'name':['Driver Arun','Passenger Meera','Outside user'][i],'email':email,'password':password,'department':'QA'})['id']);ctx.csrf=call(ctx,'/login',{'email':email,'password':password})['csrf']
  driver,rider,outsider=contexts
  with db.cursor() as q:
   q.execute("INSERT INTO rides(driver_id,origin,destination,origin_lat,origin_lng,dest_lat,dest_lng,departure,seats,available_seats,price,distance_km) VALUES(%s,'Tambaram','Tidel Park',12.9249,80.1,12.9895,80.249,DATE_ADD(NOW(),INTERVAL 1 DAY),2,2,95,19)",(ids[0],));ride=q.lastrowid
  bid=call(rider,'/book',{'ride_id':ride})['id']
  order=call(rider,'/payment/start',{'booking_id':bid,'amount':1})['payment'];assert float(order['amount'])==95;assert order['reference'].startswith('DEMO-');passed('Server uses stored fare and explicitly marks demo orders')
  assert call(rider,'/payment/start',{'booking_id':bid})['payment']['id']==order['id'];passed('Repeated checkout reuses the pending attempt')
  call(outsider,'/payment/history',{'booking_id':bid},404);call(outsider,'/payment/start',{'booking_id':bid},404);call(outsider,'/payment/finish',{'payment_id':order['id'],'outcome':'PAID','method':'UPI'},404);passed('Another user cannot read or change payment records')
  call(rider,'/payment/finish',{'payment_id':order['id'],'outcome':'FAILED','method':'UPI'});new=call(rider,'/payment/start',{'booking_id':bid})['payment'];assert new['id']!=order['id'];passed('Failed payment can be retried with a new attempt')
  call(rider,'/payment/finish',{'payment_id':new['id'],'outcome':'CANCELLED','method':'CARD'});assert call(rider,'/mine')['bookings'][0]['status']=='CONFIRMED';passed('Cancelling checkout preserves the seat booking')
  page=rider.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE);page.locator('.hero').wait_for();page.locator('nav [data-page=mine]').click();page.locator(f'[data-payment="{bid}"]').click();page.get_by_text('CHECKOUT',exact=True).wait_for();page.locator('[data-payment-outcome=PAID]').click();page.get_by_text('Payment successful. No money was charged in test mode.',exact=True).wait_for();passed('Browser checkout records a successful simulated payment')
  page.screenshot(path=str(ROOT/'docs/screenshots/09-demo-payment.png'),full_page=True)
  paid=call(rider,'/payment/history',{'booking_id':bid})['payments'][0];assert paid['status']=='PAID';assert call(rider,'/payment/start',{'booking_id':bid})['payment']['id']==paid['id'];call(rider,'/payment/finish',{'payment_id':paid['id'],'outcome':'PAID','method':'UPI'});call(rider,'/payment/finish',{'payment_id':paid['id'],'outcome':'FAILED','method':'UPI'},409);passed('Successful payments are idempotent and cannot be overwritten')
  with page.expect_download() as download:page.locator('[data-receipt]').first.click()
  assert 'TEST MODE - NO MONEY CHARGED' in pathlib.Path(download.value.path()).read_text();page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors;passed('Demo receipt downloads and mobile checkout renders without errors')
  call(rider,'/booking/cancel',{'id':bid});assert call(rider,'/payment/history',{'booking_id':bid})['payments'][0]['status']=='REFUNDED';call(rider,'/payment/start',{'booking_id':bid},409);passed('Booking cancellation records a simulated refund and blocks checkout')
  call(rider,'/book',{'ride_id':ride});retry=call(rider,'/payment/start',{'booking_id':bid})['payment'];assert retry['id']!=paid['id'];call(rider,'/payment/finish',{'payment_id':retry['id'],'outcome':'PAID','method':'NETBANKING'});call(driver,'/ride/status',{'id':ride,'status':'CANCELLED'});assert call(rider,'/payment/history',{'booking_id':bid})['payments'][0]['status']=='REFUNDED';passed('Rebooking creates a fresh attempt; driver cancellation refunds it')
 finally:
  browser.close()
  with db.cursor() as q:
   if ride:
    q.execute('DELETE p FROM demo_payments p JOIN bookings b ON b.id=p.booking_id WHERE b.ride_id=%s',(ride,))
    for table in ['ride_chat_reads','ride_messages','bookings']:q.execute(f'DELETE FROM {table} WHERE ride_id=%s',(ride,))
    q.execute('DELETE FROM rides WHERE id=%s',(ride,))
   for uid in ids:
    q.execute('DELETE FROM audit_log WHERE user_id=%s',(uid,));q.execute('DELETE FROM users WHERE id=%s',(uid,))
  db.close()
(ROOT/'docs/PAYMENT-TEST-RESULTS.txt').write_text(datetime.now().isoformat()+'\n'+'\n'.join('PASS '+s for s in checks),encoding='utf-8')
print(f'{len(checks)} payment checks passed; fixtures removed.')


