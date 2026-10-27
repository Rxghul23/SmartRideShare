'use strict';
// Map rendering stays in the browser; authoritative road distance and fare come from Java.
const TripMap={
 mount(form){
  const f=form.elements, box=form.querySelector('.route-map'), status=form.querySelector('.route-status');
  let map, layers, sequence=0, timer, destroyed=false, mode='origin';
  const keys=['origin_lat','origin_lng','dest_lat','dest_lng'];
  if(window.L){
   map=L.map(box,{scrollWheelZoom:false,zoomAnimation:false,fadeAnimation:false,markerZoomAnimation:false}).setView([12.98,80.22],11);
   const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'}).addTo(map);
   tiles.on('tileerror',()=>{form.querySelector('.map-note').textContent='Map tiles could not load. Check your connection; location menus and routing still work.';});
   layers=L.layerGroup().addTo(map);
   map.on('click',e=>setPoint(mode,e.latlng.lat,e.latlng.lng));
  }else box.textContent='Map library could not load. Reload the page; use the location fields below.';
  function setPoint(which,lat,lng){
   if(destroyed)return;
   const origin=which==='origin';f[which].value='Custom location';
   f[origin?'origin_name':'dest_name'].value=(origin?'Pickup':'Destination')+' ('+lat.toFixed(4)+', '+lng.toFixed(4)+')';
   f[origin?'origin_lat':'dest_lat'].value=lat.toFixed(6);f[origin?'origin_lng':'dest_lng'].value=lng.toFixed(6);
   form.querySelector('#coordinates').open=true;refresh();form.dispatchEvent(new Event('tripchange'));
  }
  form.querySelectorAll('[data-map-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mapMode;form.querySelectorAll('[data-map-mode]').forEach(x=>x.classList.toggle('active',x===b));});
  form.querySelector('[data-locate]').onclick=()=>{
   if(!navigator.geolocation){status.textContent='Location is unavailable in this browser.';return;}
   navigator.geolocation.getCurrentPosition(p=>setPoint('origin',p.coords.latitude,p.coords.longitude),()=>{status.textContent='Location permission was denied or unavailable. Choose a point on the map instead.';},{timeout:10000,maximumAge:60000});
  };
  form.querySelector('[data-route-retry]').onclick=()=>refresh();
  function clearValues(){if(f.distance_km){f.distance_km.value='';f.price.value='';}form.dataset.routeReady='false';form.querySelector('.route-summary').textContent='';}
  function markers(a,b){
   if(!map)return;
   layers.clearLayers();
   [a,b].forEach((point,i)=>{
    const marker=L.marker(point,{draggable:true,icon:L.divIcon({className:'route-pin',html:i?'B':'A',iconSize:[28,28],iconAnchor:[14,28]}),title:i?'Drag destination':'Drag pickup'}).addTo(layers);
    marker.on('dragend',()=>{const p=marker.getLatLng();setPoint(i?'destination':'origin',p.lat,p.lng);});
   });
  }
  function refresh(){
   clearTimeout(timer);const ticket=++sequence;clearValues();f.destination.setCustomValidity('');
   if(layers)layers.clearLayers();
   if(keys.some(k=>f[k].value===''||!f[k].validity.valid)){status.textContent='Select two locations or enter valid coordinates.';return;}
   const [lat1,lng1,lat2,lng2]=keys.map(k=>Number(f[k].value));
   if(Math.abs(lat1-lat2)+Math.abs(lng1-lng2)<0.0001){status.textContent='Pickup and destination must be different.';f.destination.setCustomValidity(status.textContent);return;}
   const a=[lat1,lng1],b=[lat2,lng2];markers(a,b);
   if(map)map.fitBounds(L.latLngBounds([a,b]),{padding:[35,35],maxZoom:15,animate:false});
   status.textContent='Calculating driving route and price…';
   timer=setTimeout(async()=>{
    try{
     const route=await api('/route',Object.fromEntries(keys.map(k=>[k,Number(f[k].value)])));
     if(destroyed||ticket!==sequence||!form.isConnected)return;
     if(f.distance_km){f.distance_km.value=route.distance_km;f.price.value=route.price;}
     form.dataset.routeReady='true';form.dataset.routeDistance=route.distance_km;form.dataset.routePrice=route.price;
     form.querySelector('.route-summary').textContent=route.distance_km+' km · '+route.duration_min+' min · ₹'+route.price+' / seat';
     status.textContent='Road route calculated · ₹'+route.rate_per_km+'/km per seat. Travel time excludes live traffic.';
     if(map){L.geoJSON(route.geometry,{style:{color:'#214d3f',weight:5,opacity:.85}}).addTo(layers);map.invalidateSize();}
    }catch(e){if(ticket!==sequence||destroyed)return;clearValues();status.textContent=e.message;}
   },350);
  }
  refresh();return {refresh,dispose(){destroyed=true;sequence++;clearTimeout(timer);if(map){map.stop();map.remove();}}};
 }
};
