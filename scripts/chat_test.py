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
  bid=call(rider,'/book',{'ride_id':ride})['id'];assert any(r['id']==ride for r in call(rider,'/chats'));passed('Booked passenger and driver can access the same conversation')
  for path,body in [('/chat/history',{'ride_id':ride}),('/chat/read',{'ride_id':ride,'last_id':0}),('/chat/send',{'ride_id':ride,'body':'hello','client_key':str(uuid.uuid4())})]:call(outsider,path,body,403)
  assert not call(outsider,'/chats');passed('Nonparticipants cannot list, read or send ride messages')
  payload={'ride_id':ride,'body':'Meet at the main gate at 9 AM.','client_key':str(uuid.uuid4())};sent=call(driver,'/chat/send',payload);assert call(driver,'/chat/send',payload)['id']==sent['id'];call(driver,'/chat/send',{**payload,'body':'Changed'},409);passed('Message retry is idempotent and reused keys are rejected')
  assert call(rider,'/chats')[0]['unread']==1;call(rider,'/chat/read',{'ride_id':ride,'last_id':sent['id']});assert call(rider,'/chats')[0]['unread']==0;passed('Unread counts and persistent read receipts update correctly')
  pages=[ctx.new_page() for ctx in contexts[:2]];errors=[]
  for pg in pages:
   pg.on('pageerror',lambda e:errors.append(str(e)));pg.goto(BASE);pg.locator('.hero').wait_for();pg.locator('nav [data-page=chat]').click();pg.locator('#chat-form:not(.hidden)').wait_for()
  a,b=pages;b.locator('#chat-text').fill('My pickup draft');a.locator('#chat-text').fill('I will wait beside the blue sign.');a.locator('#chat-send').click();b.locator('#chat-messages').get_by_text('I will wait beside the blue sign.',exact=True).wait_for(timeout=12000);assert b.locator('#chat-text').input_value()=='My pickup draft';passed('Messages arrive in a second browser automatically without losing drafts')
  b.locator('#chat-text').fill('Thanks, I will be there on time.');b.locator('#chat-send').click();a.locator('#chat-messages').get_by_text('Thanks, I will be there on time.',exact=True).wait_for(timeout=12000)
  a.screenshot(path=str(ROOT/'docs/screenshots/08-ride-chat.png'),full_page=True)
  unsafe='<img src=x onerror="window.chatInjected=true">';call(driver,'/chat/send',{'ride_id':ride,'body':unsafe,'client_key':str(uuid.uuid4())});b.locator('#chat-messages').get_by_text(unsafe,exact=True).wait_for(timeout=12000);assert not b.evaluate('Boolean(window.chatInjected)');assert b.locator('#chat-messages img').count()==0;passed('Message markup is displayed as text and cannot execute')
  b.reload();b.locator('.hero').wait_for();b.locator('nav [data-page=chat]').click();b.locator('#chat-messages').get_by_text('Thanks, I will be there on time.',exact=True).wait_for();passed('Conversation survives page reload')
  b.set_viewport_size({'width':390,'height':844});assert b.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors;passed('Chat renders on mobile without horizontal overflow or JavaScript errors')
  with db.cursor() as q:
   q.executemany('INSERT INTO ride_messages(ride_id,sender_id,body,client_key) VALUES(%s,%s,%s,%s)',[(ride,ids[0],f'History message {i}',str(uuid.uuid4())) for i in range(105)])
  latest=call(rider,'/chat/history',{'ride_id':ride});assert len(latest['messages'])==100 and latest['has_more'];older=call(rider,'/chat/history',{'ride_id':ride,'before_id':latest['messages'][0]['id']});assert older['messages'] and older['messages'][-1]['id']<latest['messages'][0]['id'];passed('Older message pagination preserves chronological order')
  call(rider,'/booking/cancel',{'id':bid});call(rider,'/chat/history',{'ride_id':ride},403);passed('Cancelling a booking revokes chat access')
  with db.cursor() as q:q.execute("UPDATE rides SET status='COMPLETED' WHERE id=%s",(ride,))
  assert not call(driver,'/chat/history',{'ride_id':ride})['can_send'];call(driver,'/chat/send',{'ride_id':ride,'body':'Closed','client_key':str(uuid.uuid4())},409);passed('Closed rides retain read-only history and reject new messages')
 finally:
  browser.close()
  with db.cursor() as q:
   if ride:
    for table in ['ride_chat_reads','ride_messages','bookings']:q.execute(f'DELETE FROM {table} WHERE ride_id=%s',(ride,))
    q.execute('DELETE FROM rides WHERE id=%s',(ride,))
   for uid in ids:
    q.execute('DELETE FROM audit_log WHERE user_id=%s',(uid,));q.execute('DELETE FROM users WHERE id=%s',(uid,))
  db.close()
(ROOT/'docs/CHAT-TEST-RESULTS.txt').write_text(datetime.now().isoformat()+'\n'+'\n'.join('PASS '+s for s in checks),encoding='utf-8')
print(f'{len(checks)} chat checks passed; fixtures removed.')

