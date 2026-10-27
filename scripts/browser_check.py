import json,pathlib
from playwright.sync_api import sync_playwright
root=pathlib.Path(r'Z:\CAO-DA'); config=json.loads((root/'.local-config.json').read_text()); out=root/'docs/screenshots';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8080/smartride/');page.screenshot(path=str(out/'01-login.png'),full_page=True)
 page.locator('[name=email]').fill('admin@smartride.local');page.locator('[name=password]').fill(config['demoPassword']);page.locator('#auth-submit').click()
 page.locator('.hero').wait_for(timeout=20000);page.screenshot(path=str(out/'02-dashboard.png'),full_page=True)
 for target in ['find','offer','mine','analytics','admin']:
  page.locator('nav [data-page='+target+']').click();page.locator('#content .page-heading').wait_for();page.screenshot(path=str(out/('03-'+target+'.png')),full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.locator('nav [data-page=dashboard]').click();page.locator('.hero').wait_for();page.screenshot(path=str(out/'04-mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile horizontal overflow'
 assert not errors, errors
 print('Browser pages rendered. No JavaScript errors. Mobile width passed.')
 browser.close()
