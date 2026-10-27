package com.smartride;

import com.google.gson.JsonObject;
import java.sql.*;
import java.util.*;

/** Participant-only group conversations. A cancellation revokes passenger access. */
public final class Chat {
 private Chat() {}
 public static Object list(Connection c,long uid)throws SQLException {
  return Db.query(c,"SELECT r.id,r.origin,r.destination,r.departure,r.status,r.driver_id,u.name driver,"+
   "(SELECT body FROM ride_messages WHERE ride_id=r.id ORDER BY id DESC LIMIT 1) last_message,"+
   "(SELECT MAX(id) FROM ride_messages WHERE ride_id=r.id) last_message_id,"+
   "(SELECT COUNT(*) FROM ride_messages m WHERE m.ride_id=r.id AND m.sender_id<>? AND m.id>COALESCE(cr.last_message_id,0)) unread "+
   "FROM rides r JOIN users u ON u.id=r.driver_id LEFT JOIN ride_chat_reads cr ON cr.ride_id=r.id AND cr.user_id=? "+
   "WHERE r.driver_id=? OR EXISTS(SELECT 1 FROM bookings b WHERE b.ride_id=r.id AND b.passenger_id=? AND b.status IN ('CONFIRMED','COMPLETED')) "+
   "ORDER BY COALESCE(last_message_id,0) DESC,r.departure DESC",uid,uid,uid,uid);
 }
 private static Map<String,Object> access(Connection c,long uid,long rideId,boolean lock)throws SQLException {
  var r=Db.one(c,"SELECT id,origin,destination,departure,driver_id,status FROM rides WHERE id=?"+(lock?" FOR UPDATE":""),rideId);
  if(Api.num(r,"driver_id")!=uid && Db.query(c,"SELECT id FROM bookings WHERE ride_id=? AND passenger_id=? AND status IN ('CONFIRMED','COMPLETED')",rideId,uid).isEmpty())
   throw new Api.Error(403,"Ride chat is available only to the driver and booked passengers. A cancelled booking no longer has access.");
  return r;
 }
 public static Object history(Connection c,long uid,JsonObject body)throws SQLException {
  long id=Api.integer(body,"ride_id",1,Long.MAX_VALUE);
  long before=body.has("before_id")?Api.integer(body,"before_id",0,Long.MAX_VALUE):0;
  long after=body.has("after_id")?Api.integer(body,"after_id",0,Long.MAX_VALUE):0;
  if(before>0&&after>0)throw new Api.Error(400,"Use one history cursor at a time.");
  var ride=access(c,uid,id,false);
  String sql="SELECT m.id,m.ride_id,m.sender_id,u.name sender,m.body,m.created_at FROM ride_messages m JOIN users u ON u.id=m.sender_id WHERE m.ride_id=?";
  List<Map<String,Object>> messages;
  if(after>0)messages=Db.query(c,sql+" AND m.id>? ORDER BY m.id LIMIT 100",id,after);
  else if(before>0)messages=Db.query(c,sql+" AND m.id<? ORDER BY m.id DESC LIMIT 100",id,before);
  else messages=Db.query(c,sql+" ORDER BY m.id DESC LIMIT 100",id);
  boolean more=messages.size()==100;
  if(after==0)Collections.reverse(messages);
  var people=Db.query(c,"SELECT id,name FROM users WHERE id=? OR id IN (SELECT passenger_id FROM bookings WHERE ride_id=? AND status IN ('CONFIRMED','COMPLETED')) ORDER BY id",ride.get("driver_id"),id);
  return Map.of("ride",ride,"messages",messages,"participants",people,"can_send","OPEN".equals(ride.get("status")),"has_more",more);
 }
 public static Object send(Connection c,long uid,JsonObject body)throws SQLException {
  long id=Api.integer(body,"ride_id",1,Long.MAX_VALUE);
  String message=Api.text(body,"body",2000), key=Api.text(body,"client_key",36);
  try {if(!UUID.fromString(key).toString().equalsIgnoreCase(key))throw new IllegalArgumentException();}
  catch(IllegalArgumentException e){throw new Api.Error(400,"Invalid message reference.");}
  c.setAutoCommit(false);
  try {
   var ride=access(c,uid,id,true);
   var old=Db.query(c,"SELECT id,ride_id,body FROM ride_messages WHERE sender_id=? AND client_key=?",uid,key);
   if(!old.isEmpty()) {
    if(Api.num(old.get(0),"ride_id")!=id||!message.equals(old.get(0).get("body")))throw new Api.Error(409,"Message reference was already used.");
    c.commit();return Map.of("id",old.get(0).get("id"),"duplicate",true);
   }
   if(!"OPEN".equals(ride.get("status")))throw new Api.Error(409,"This ride is closed. Its conversation is read-only.");
   long messageId=Db.update(c,"INSERT INTO ride_messages(ride_id,sender_id,body,client_key) VALUES(?,?,?,?)",id,uid,message,key);
   c.commit();return Map.of("id",messageId,"duplicate",false);
  }catch(Exception e){c.rollback();throw e;}finally{c.setAutoCommit(true);}
 }
 public static Object read(Connection c,long uid,JsonObject body)throws SQLException {
  long id=Api.integer(body,"ride_id",1,Long.MAX_VALUE),last=Api.integer(body,"last_id",0,Long.MAX_VALUE);
  access(c,uid,id,false);
  var row=Db.one(c,"SELECT COALESCE(MAX(id),0) last_id FROM ride_messages WHERE ride_id=? AND id<=?",id,last);
  Db.update(c,"INSERT INTO ride_chat_reads(ride_id,user_id,last_message_id) VALUES(?,?,?) ON DUPLICATE KEY UPDATE last_message_id=GREATEST(last_message_id,VALUES(last_message_id))",id,uid,row.get("last_id"));
  return Map.of("ok",true);
 }
}
