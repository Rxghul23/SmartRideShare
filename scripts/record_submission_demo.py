"""Capture a captioned walkthrough of real browser actions using isolated accounts."""
from pathlib import Path
import json,uuid,subprocess
from datetime import datetime
import pymysql,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/submission_assets';OUT.mkdir(parents=True,exist_ok=True)
TMP=ROOT/'tmp/submission_demo';TMP.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'.local-config.json').read_text());BASE='http://127.0.0.1:8080/smartride/';ids=[];rid=None;shots=[];tag=uuid.uuid4().hex[:8]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
def capture(pg,label,name):
 pg.wait_for_timeout(800);path=TMP/f'{len(shots):02}.png';pg.screenshot(path=str(path));im=Image.open(path).convert('RGB');draw=ImageDraw.Draw(im);draw.rectangle((0,730,1440,810),fill='#183f35');draw.text((30,750),label,font=font,fill='white');im.save(path);shots.append((path,label));pg.screenshot(path=str(OUT/f'{name}.png'));print(label,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
 contexts=[browser.new_context(viewport={'width':1440,'height':810}) for _ in range(3)]
 def api(ctx,path,body=None):
  r=ctx.request.get(BASE+'api'+path) if body is None else ctx.request.post(BASE+'api'+path,data=body,headers={'X-CSRF-Token':getattr(ctx,'csrf','')});assert r.ok,(path,r.status,r.text());return r.json()
 def route(pg,selector):
  for attempt in range(3):
   try:pg.locator(selector+'[data-route-ready="true"]').wait_for(timeout=22000);return
   except Exception:
    if attempt==2:raise
    pg.locator(selector+' [data-route-retry]').click()
 try:
  driver,rider,admin=contexts;emails=[]
  for i,ctx in enumerate([driver,rider]):
   email=f'review-{tag}-{i}@example.test';emails.append(email);ids.append(api(ctx,'/register',{'name':['Arun - Driver','Meera - Passenger'][i],'email':email,'password':'ReviewRide!2026','department':'Review 3'})['id'])
  a=driver.new_page();a.goto(BASE);capture(a,'01  Sign in to access the Ride, Analytics and Admin modules','login')
  a.locator('[name=email]').fill(emails[0]);a.locator('[name=password]').fill('ReviewRide!2026');a.locator('#auth-submit').click();a.locator('.hero').wait_for();driver.csrf=api(driver,'/me')['csrf'];capture(a,'02  Driver dashboard: offer available seats to the community','dashboard')
  a.locator('nav [data-page=offer]').click();route(a,'#offer-form');a.locator('[name=seats]').fill('2');capture(a,'03  Select pickup, destination, time and seats; distance and fare update','offer')
  a.locator('.route-map').scroll_into_view_if_needed();capture(a,'04  Road route on the map; price is INR 5 per kilometre per seat','map')
  a.locator('#offer-form button.primary').click();a.locator('[data-ride-status=CANCELLED]').wait_for();rid=api(driver,'/mine')['offers'][0]['id'];capture(a,'05  Ride published with two available passenger seats','published')
  b=rider.new_page();b.goto(BASE);b.locator('[name=email]').fill(emails[1]);b.locator('[name=password]').fill('ReviewRide!2026');b.locator('#auth-submit').click();b.locator('.hero').wait_for();rider.csrf=api(rider,'/me')['csrf'];b.locator('nav [data-page=find]').click();route(b,'#find-form');b.locator('#find-form button.primary').click();b.get_by_text('Request saved. AI is watching for compatible rides.',exact=True).wait_for();b.locator('nav [data-page=ai]').click();b.locator(f'[data-book="{rid}"]').wait_for(timeout=18000);b.locator(f'[data-book="{rid}"]').scroll_into_view_if_needed();capture(b,'06  A different user receives the matching ride automatically','matching')
  b.locator(f'[data-book="{rid}"]').click();b.locator('[data-payment]').wait_for();capture(b,'07  Passenger confirms the booking; one seat is reserved','booking')
  b.locator('[data-payment]').click();b.locator('[data-payment-outcome=PAID]').wait_for();capture(b,'08  Checkout offers UPI, card and net banking in test mode','checkout')
  b.locator('[data-payment-outcome=PAID]').click();b.get_by_text('Payment successful. No money was charged in test mode.',exact=True).wait_for();capture(b,'09  Payment recorded with a receipt; no money is charged','receipt');b.locator('#payment-close').click()
  b.locator('nav [data-page=chat]').click();b.locator('#chat-form:not(.hidden)').wait_for();b.locator('#chat-text').fill('I will wait near the main gate.');b.locator('#chat-send').click();b.locator('#chat-messages').get_by_text('I will wait near the main gate.',exact=True).wait_for();capture(b,'10  Booked passengers can coordinate pickup through ride chat','chat-passenger')
  a.locator('nav [data-page=chat]').click();a.locator('#chat-messages').get_by_text('I will wait near the main gate.',exact=True).wait_for();a.locator('#chat-text').fill('Confirmed. I will meet you there.');a.locator('#chat-send').click();b.locator('#chat-messages').get_by_text('Confirmed. I will meet you there.',exact=True).wait_for(timeout=12000);capture(b,'11  The driver reply arrives automatically in the passenger account','chat')
  b.locator('nav [data-page=mine]').click();b.locator('[data-cancel-booking]').wait_for();b.once('dialog',lambda d:d.accept());b.locator('[data-cancel-booking]').click();b.get_by_text('REFUNDED',exact=True).wait_for();capture(b,'12  Cancelling the booking releases its seat and records a test refund','refund')
  # Read-only administrator views show existing application analytics and health.
  adm=admin.new_page();adm.goto(BASE);adm.locator('[name=email]').fill('admin@smartride.local');adm.locator('[name=password]').fill(CFG['demoPassword']);adm.locator('#auth-submit').click();adm.locator('.hero').wait_for();adm.locator('nav [data-page=analytics]').click();adm.get_by_text('Every shared ride adds up.',exact=True).wait_for();capture(adm,'13  Analytics summarises recorded journeys and estimated impact','analytics')
  adm.locator('nav [data-page=admin]').click();adm.locator('#content .page-heading').wait_for();capture(adm,'14  Administrators manage accounts, rides, settings and service health','admin')
 finally:
  browser.close();db=pymysql.connect(host='127.0.0.1',port=3307,user='smartride',password=CFG['dbPassword'],database='smartride',autocommit=True)
  with db.cursor() as q:
   if rid:
    q.execute('DELETE p FROM demo_payments p JOIN bookings b ON b.id=p.booking_id WHERE b.ride_id=%s',(rid,))
    for t in ['ride_chat_reads','ride_messages']:q.execute(f'DELETE FROM {t} WHERE ride_id=%s',(rid,))
   for uid in ids:
    q.execute('DELETE m FROM match_history m JOIN ride_requests r ON r.id=m.request_id WHERE r.user_id=%s',(uid,));q.execute('DELETE FROM bookings WHERE passenger_id=%s',(uid,));q.execute('DELETE FROM ride_requests WHERE user_id=%s',(uid,));q.execute('DELETE FROM audit_log WHERE user_id=%s',(uid,))
   for uid in ids:q.execute('DELETE FROM rides WHERE driver_id=%s',(uid,))
   for uid in ids:q.execute('DELETE FROM users WHERE id=%s',(uid,))
  db.close()
assert len(shots)==14
manifest=TMP/'frames.txt';manifest.write_text('\n'.join("file '"+str(path).replace('\\','/')+"'\nduration 7" for path,label in shots)+"\nfile '"+str(shots[-1][0]).replace('\\','/')+"'\n",encoding='utf-8')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','concat','-safe','0','-i',str(manifest),'-vf','fps=12','-c:v','libx264','-pix_fmt','yuv420p','-crf','23','-movflags','+faststart',str(OUT/'SmartRideShare_Demo.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(OUT/'Demo_Chapters.txt').write_text('Captioned walkthrough of actual local browser actions. No audio.\nCaptured 24 October 2026. Payment uses test mode.\n\n'+'\n'.join(f'{i*7//60:02}:{i*7%60:02}  {label}' for i,(_,label) in enumerate(shots))+'\n\nCompletion and feedback: a driver completes a ride only after departure; the passenger may then rate it. Future departures cannot be completed.\n',encoding='utf-8')
print('Recorded 14 verified steps; temporary accounts removed.',flush=True)
