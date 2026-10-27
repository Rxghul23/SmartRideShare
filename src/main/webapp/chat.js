'use strict';
const RideChat=(()=>{
 let rideId=0,preferred=0,generation=0,lastId=0,firstId=0,busy=false,more=false,seen=new Set(),drafts=new Map(),retryKeys=new Map();
 const saveDraft=()=>{const input=document.querySelector('#chat-text');if(input&&rideId)drafts.set(rideId,input.value);};
 function leave(){saveDraft();generation++;rideId=0;lastId=0;firstId=0;seen.clear();}
 function reset(){leave();preferred=0;drafts.clear();retryKeys.clear();const badge=document.querySelector('#chat-badge');if(badge){badge.textContent='';badge.classList.add('hidden');}}
 function badge(rows){const count=rows.reduce((n,r)=>n+Number(r.unread),0),el=$('#chat-badge');if(el){el.textContent=count>99?'99+':String(count);el.classList.toggle('hidden',!count);}}
 function list(rows){const el=$('#chat-list');if(!el)return;const html=rows.map(r=>`<button class="chat-choice ${r.id===rideId?'selected':''}" data-chat-select="${r.id}"><strong>${esc(r.origin)} → ${esc(r.destination)}</strong><small>${when(r.departure)} · ${esc(r.status)}</small><span>${esc(r.last_message||'Start the conversation')}</span>${Number(r.unread)>0?`<b class="chat-count">${r.unread}</b>`:''}</button>`).join('')||empty('No ride conversations','Book a seat or offer a ride to start chatting.');if(el.innerHTML!==html)el.innerHTML=html;}
 async function mount(){
  $('#content').innerHTML=heading('Ride chat','Coordinate pickup with your driver and fellow passengers. Updates every 3 seconds.')+`<section class="chat-layout"><aside class="chat-sidebar"><h3>Your conversations</h3><div id="chat-list"></div></aside><section class="chat-thread"><header id="chat-heading"><h2>Select a ride</h2><p class="muted">Only the driver and booked passengers can access its conversation.</p></header><button id="chat-older" class="text-button hidden" type="button">Load earlier messages</button><div id="chat-messages" role="log" aria-label="Ride messages" aria-live="polite">${empty('Keep pickup simple','Choose a conversation on the left.')}</div><p id="chat-status" role="status"></p><form id="chat-form" class="hidden"><label for="chat-text">Message your ride group</label><textarea id="chat-text" maxlength="2000" rows="2" placeholder="For example: I am near the main gate." required></textarea><div class="chat-compose-footer"><small>Visible to this ride’s participants · Ctrl+Enter to send</small><button class="primary" id="chat-send">Send ↗</button></div></form></section></section>`;
  $('#chat-form').onsubmit=send;$('#chat-text').oninput=saveDraft;$('#chat-text').onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();$('#chat-form').requestSubmit();}};
  $('#chat-older').onclick=older;
  const ticket=generation,rows=await api('/chats');if(page!=='chat'||ticket!==generation)return;badge(rows);list(rows);
  const wanted=preferred;preferred=0;
  if(wanted&&!rows.some(r=>r.id===wanted)){$('#chat-status').textContent='This conversation is no longer available to your account.';return;}
  if(rows.length)await select(wanted||rows[0].id);
 }
 async function select(id){
  saveDraft();generation++;rideId=id;lastId=0;firstId=0;seen.clear();more=false;
  $('#chat-send').disabled=false;$('#chat-older').disabled=false;
  $('#chat-messages').innerHTML='';$('#chat-heading').innerHTML='<h2>Loading conversation…</h2>';$('#chat-status').textContent='';$('#chat-older').classList.add('hidden');$('#chat-form').classList.add('hidden');$('#chat-text').value=drafts.get(id)||'';
  await history();const ticket=generation,rows=await api('/chats');if(ticket===generation&&page==='chat'){list(rows);badge(rows);}
 }
 function bubble(m){return `<article class="chat-message ${Number(m.sender_id)===Number(user.id)?'own':''}" data-message-id="${m.id}"><div><strong>${Number(m.sender_id)===Number(user.id)?'You':esc(m.sender)}</strong><time>${when(m.created_at)}</time></div><p>${esc(m.body)}</p></article>`;}
 async function history(){
  if(!rideId||page!=='chat')return;const id=rideId,ticket=generation;
  try{
   const data=await api('/chat/history',{ride_id:id,after_id:lastId});if(ticket!==generation||page!=='chat')return;
   $('#chat-heading').innerHTML=`<h2>${esc(data.ride.origin)} → ${esc(data.ride.destination)}</h2><p>${when(data.ride.departure)} · ${esc(data.ride.status)} · ${data.participants.length} participants</p><small>${data.participants.map(p=>esc(p.name)).join(' · ')}</small>`;
   const box=$('#chat-messages'),nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<90,initial=lastId===0;
   if(initial){box.innerHTML='';more=data.has_more;$('#chat-older').classList.toggle('hidden',!more);}
   for(const message of data.messages){if(seen.has(message.id))continue;seen.add(message.id);box.insertAdjacentHTML('beforeend',bubble(message));lastId=Math.max(lastId,message.id);firstId=firstId?Math.min(firstId,message.id):message.id;}
   if(!seen.size)box.innerHTML=empty('No messages yet','Start by confirming the pickup point.');
   else box.querySelector('.empty')?.remove();
   if(initial||nearBottom)box.scrollTop=box.scrollHeight;
   $('#chat-form').classList.toggle('hidden',!data.can_send);$('#chat-status').textContent=data.can_send?'':'This ride is closed. Previous messages remain available to current participants.';
   if(lastId)await api('/chat/read',{ride_id:id,last_id:lastId});
  }catch(e){if(ticket!==generation||page!=='chat')return;$('#chat-status').textContent=e.message;$('#chat-messages').innerHTML='';$('#chat-form').classList.add('hidden');$('#chat-older').classList.add('hidden');seen.clear();lastId=0;firstId=0;}
 }
 async function older(){
  if(!firstId||!more)return;const ticket=generation,id=rideId;$('#chat-older').disabled=true;
  try{const data=await api('/chat/history',{ride_id:id,before_id:firstId});if(ticket!==generation)return;const box=$('#chat-messages'),height=box.scrollHeight;
   const messages=data.messages.filter(m=>!seen.has(m.id));messages.forEach(m=>{seen.add(m.id);firstId=Math.min(firstId,m.id);});box.insertAdjacentHTML('afterbegin',messages.map(bubble).join(''));box.scrollTop+=box.scrollHeight-height;more=data.has_more;$('#chat-older').classList.toggle('hidden',!more);
  }catch(e){if(ticket===generation)$('#chat-status').textContent=e.message;}finally{if(ticket===generation)$('#chat-older').disabled=false;}
 }
 async function send(event){
  event.preventDefault();const input=$('#chat-text'),raw=input.value,body=raw.trim(),id=rideId,ticket=generation;
  if(!body){input.setCustomValidity('Enter a message before sending.');input.reportValidity();input.setCustomValidity('');return;}
  if($('#chat-send').disabled)return;
  const old=retryKeys.get(id),key=old?.body===body?old.key:crypto.randomUUID();retryKeys.set(id,{body,key});$('#chat-send').disabled=true;
  try{await api('/chat/send',{ride_id:id,body,client_key:key});retryKeys.delete(id);if(drafts.get(id)===raw)drafts.delete(id);
   if(ticket!==generation||page!=='chat')return;if(input.value===raw)input.value='';await history();
  }catch(e){if(ticket===generation&&page==='chat')$('#chat-status').textContent=e.message+' Your draft is kept; retry when ready.';}
  finally{if(ticket===generation&&page==='chat')$('#chat-send').disabled=false;}
 }
 async function poll(){if(busy||!user||document.hidden)return;busy=true;const account=user.id,ticket=generation;
  try{const rows=await api('/chats');if(!user||user.id!==account)return;badge(rows);if(page==='chat'&&ticket===generation){list(rows);await history();}}catch(e){if(page==='chat'&&$('#chat-status'))$('#chat-status').textContent='Connection interrupted. Retrying automatically; your draft is kept.';}finally{busy=false;}}
 document.addEventListener('click',async e=>{const selectButton=e.target.closest('[data-chat-select]'),open=e.target.closest('[data-open-chat]');try{if(selectButton)await select(Number(selectButton.dataset.chatSelect));if(open){preferred=Number(open.dataset.openChat);await navigate('chat');}}catch(e){toast(e.message);}});
 setInterval(poll,3000);
 return {mount,leave,reset,poll};
})();
