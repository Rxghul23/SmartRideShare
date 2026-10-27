'use strict';
const DemoPayment=(()=>{
 let bookingId=0,payment=null,busy=false;
 const dialog=()=>document.querySelector('#payment-dialog');
 async function show(id){bookingId=id;payment=null;dialog().showModal();await render();}
 async function render(){
  const data=await api('/payment/history',{booking_id:bookingId}),b=data.booking,latest=data.payments[0];
  $('#payment-body').innerHTML=`<span class="pill">CHECKOUT</span><h2>Pay for your shared ride</h2><p>${esc(b.origin)} → ${esc(b.destination)}</p><h2>${money(b.price)} <small>INR · one seat</small></h2><p class="muted">Test mode · No money will be charged.</p>${b.status!=='CANCELLED'&&latest?.status!=='PAID'?`<label>Payment method<select id="payment-method"><option value="UPI">UPI</option><option value="CARD">Card</option><option value="NETBANKING">Net banking</option></select></label><div class="payment-actions"><button class="primary" data-payment-outcome="PAID">Pay now</button><button class="secondary" data-payment-outcome="FAILED">Test failure</button><button class="secondary" data-payment-outcome="CANCELLED">Cancel</button></div>`:''}<p id="payment-error" role="status"></p><h3>Payment history</h3>${data.payments.map(p=>`<div class="payment-record"><strong>${esc(p.status)} · ${money(p.amount)}</strong><small>${esc(p.reference.replace(/^DEMO-/, 'PAY-'))}</small><small>${esc(p.method)} · ${when(p.updated_at)}</small>${['PAID','REFUNDED'].includes(p.status)?`<button class="text-button" data-receipt="${p.id}">Download receipt</button>`:''}</div>`).join('')||'<p class="muted">No payment attempts yet.</p>'}`;
  if(latest?.status==='PAID')$('#payment-error').textContent='Payment successful. No money was charged in test mode.';
 }
 async function finish(outcome){
  if(busy)return;busy=true;const method=$('#payment-method').value;dialog().querySelectorAll('[data-payment-outcome]').forEach(b=>b.disabled=true);
  try{payment=(await api('/payment/start',{booking_id:bookingId})).payment;await api('/payment/finish',{payment_id:payment.id,outcome,method});await render();if(page==='mine')await minePage();}
  catch(e){$('#payment-error').textContent=e.message;dialog().querySelectorAll('[data-payment-outcome]').forEach(b=>b.disabled=false);}finally{busy=false;}
 }
 async function receipt(id){const data=await api('/payment/history',{booking_id:bookingId}),p=data.payments.find(p=>p.id===id);if(!p)return;const text=['SMART RIDE SHARE - PAYMENT RECEIPT','TEST MODE - NO MONEY CHARGED','Reference: '+p.reference.replace(/^DEMO-/, 'PAY-'),'Booking: '+bookingId,'Route: '+data.booking.origin+' to '+data.booking.destination,'Amount: INR '+p.amount,'Status: '+p.status,'Method: '+p.method,'Updated: '+p.updated_at].join('\r\n');const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='SmartRide-receipt-'+p.id+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 document.addEventListener('click',async e=>{try{const open=e.target.closest('[data-payment]'),outcome=e.target.closest('[data-payment-outcome]'),download=e.target.closest('[data-receipt]');if(open)await show(Number(open.dataset.payment));if(outcome)await finish(outcome.dataset.paymentOutcome);if(download)await receipt(Number(download.dataset.receipt));if(e.target.closest('#payment-close')&&!busy)dialog().close();}catch(e){toast(e.message);}});
 document.addEventListener('DOMContentLoaded',()=>dialog().addEventListener('cancel',e=>{if(busy)e.preventDefault();}));
 return {reset(){if(dialog()?.open)dialog().close();bookingId=0;payment=null;}};
})();
