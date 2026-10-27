package com.smartride;
import com.google.gson.JsonObject;
import java.sql.*;
import java.util.*;

/** Local simulation only. No gateway SDK, credentials or money movement. */
public final class Payments {
 private Payments(){}
 private static Map<String,Object> lockBooking(Connection c,long uid,long id)throws SQLException {
  var b=Db.one(c,"SELECT ride_id FROM bookings WHERE id=? AND passenger_id=?",id,uid);
  Db.one(c,"SELECT id FROM rides WHERE id=? FOR UPDATE",b.get("ride_id"));
  return Db.one(c,"SELECT b.*,r.price,r.origin,r.destination FROM bookings b JOIN rides r ON r.id=b.ride_id WHERE b.id=? AND b.passenger_id=? FOR UPDATE",id,uid);
 }
 public static Object history(Connection c,long uid,JsonObject body)throws SQLException {
  long id=Api.integer(body,"booking_id",1,Long.MAX_VALUE);
  var b=Db.one(c,"SELECT b.id,b.status,r.price,r.origin,r.destination FROM bookings b JOIN rides r ON r.id=b.ride_id WHERE b.id=? AND b.passenger_id=?",id,uid);
  return Map.of("booking",b,"payments",Db.query(c,"SELECT * FROM demo_payments WHERE booking_id=? ORDER BY id DESC",id),"mode","SIMULATED");
 }
 public static Object start(Connection c,long uid,JsonObject body)throws SQLException {
  long id=Api.integer(body,"booking_id",1,Long.MAX_VALUE);c.setAutoCommit(false);
  try {
   var b=lockBooking(c,uid,id);if("CANCELLED".equals(b.get("status")))throw new Api.Error(409,"Cancelled bookings cannot be paid.");
   var rows=Db.query(c,"SELECT * FROM demo_payments WHERE booking_id=? AND status IN ('PENDING','PAID') ORDER BY id DESC LIMIT 1",id);
   Map<String,Object> payment;
   if(!rows.isEmpty())payment=rows.get(0);
   else {long pid=Db.update(c,"INSERT INTO demo_payments(booking_id,reference,amount) VALUES(?,?,?)",id,"DEMO-"+UUID.randomUUID(),b.get("price"));payment=Db.one(c,"SELECT * FROM demo_payments WHERE id=?",pid);}
   c.commit();return Map.of("payment",payment,"mode","SIMULATED");
  }catch(Exception e){c.rollback();throw e;}finally{c.setAutoCommit(true);}
 }
 public static Object finish(Connection c,long uid,JsonObject body)throws SQLException {
  long id=Api.integer(body,"payment_id",1,Long.MAX_VALUE);String outcome=Api.text(body,"outcome",12),method=Api.text(body,"method",12);
  if(!Set.of("PAID","FAILED","CANCELLED").contains(outcome)||!Set.of("UPI","CARD","NETBANKING").contains(method))throw new Api.Error(400,"Choose a valid demo outcome and payment method.");
  c.setAutoCommit(false);
  try {
   var first=Db.one(c,"SELECT p.booking_id FROM demo_payments p JOIN bookings b ON b.id=p.booking_id WHERE p.id=? AND b.passenger_id=?",id,uid);
   var booking=lockBooking(c,uid,Api.num(first,"booking_id"));var payment=Db.one(c,"SELECT * FROM demo_payments WHERE id=? FOR UPDATE",id);
   if(!"PENDING".equals(payment.get("status"))){if(!outcome.equals(payment.get("status")))throw new Api.Error(409,"This payment attempt is already closed.");}
   else {
    if("CANCELLED".equals(booking.get("status")))throw new Api.Error(409,"The booking was cancelled. Start with an active booking.");
    Db.update(c,"UPDATE demo_payments SET status=?,method=? WHERE id=?",outcome,method,id);
   }
   payment=Db.one(c,"SELECT * FROM demo_payments WHERE id=?",id);c.commit();return Map.of("payment",payment,"mode","SIMULATED");
  }catch(Exception e){c.rollback();throw e;}finally{c.setAutoCommit(true);}
 }
 public static void cancel(Connection c,long bookingId)throws SQLException {
  Db.update(c,"UPDATE demo_payments SET status=IF(status='PAID','REFUNDED','CANCELLED') WHERE booking_id=? AND status IN ('PAID','PENDING')",bookingId);
 }
 public static void cancelRide(Connection c,long rideId)throws SQLException {
  Db.update(c,"UPDATE demo_payments p JOIN bookings b ON b.id=p.booking_id SET p.status=IF(p.status='PAID','REFUNDED','CANCELLED') WHERE b.ride_id=? AND p.status IN ('PAID','PENDING')",rideId);
 }
}
