import json,pathlib
from playwright.sync_api import sync_playwright
root=pathlib.Path(r'Z:\CAO-DA');cfg=json.loads((root/'.local-config.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1000})
 page.goto('http://127.0.0.1:8080/smartride/')
 page.locator('[name=email]').fill('aarav@smartride.local');page.locator('[name=password]').fill(cfg['demoPassword']);page.locator('#auth-submit').click();page.locator('.hero').wait_for()
 page.locator('nav [data-page=find]').click();page.locator('#find-form').wait_for();page.locator('#find-form button.primary').click();page.locator('#matches [data-book]').first.wait_for(timeout=20000)
 page.screenshot(path=str(root/'docs/screenshots/05-matches.png'),full_page=True)
 req=int(page.locator('#matches [data-book]').first.get_attribute('data-request'))
 page.locator('#matches [data-book]').first.click();page.locator('[data-cancel-booking]').first.wait_for();page.on('dialog',lambda d:d.accept());page.locator('[data-cancel-booking]').first.click();page.get_by_text('Booking cancelled',exact=True).wait_for()
 page.locator('[data-tab=requests]').click();page.locator('[data-cancel-request="'+str(req)+'"]').click();page.get_by_text('Request cancelled',exact=True).wait_for()
 page.locator('#logout').click();page.locator('#auth-submit').wait_for();browser.close()
 print('Browser form flow passed: sign in, find matches, book, cancel, cancel request, sign out.')
# Remove only this browser test's cancelled request, match and booking records.
import pymysql
c=pymysql.connect(host='127.0.0.1',port=3307,user='smartride',password=cfg['dbPassword'],database='smartride',autocommit=True)
with c.cursor() as q:
 q.execute("DELETE FROM bookings WHERE request_id=%s AND status='CANCELLED'",(req,))
 q.execute('DELETE FROM match_history WHERE request_id=%s',(req,))
 q.execute("DELETE FROM ride_requests WHERE id=%s AND status='CANCELLED'",(req,))
c.close()
