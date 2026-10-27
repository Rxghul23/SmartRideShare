package com.smartride;

import com.google.gson.*;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.*;
import java.io.*;
import java.sql.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@WebServlet("/api/*")
public class Api extends HttpServlet {
 public static final Gson JSON=new Gson();
 public static class Error extends RuntimeException { public final int status; public Error(int s,String m) { super(m);status=s; } }
 private static final Map<String,long[]> ATTEMPTS=new ConcurrentHashMap<>();
 @Override protected void service(HttpServletRequest req,HttpServletResponse res) throws IOException {
  res.setCharacterEncoding("UTF-8"); res.setContentType("application/json"); res.setHeader("Cache-Control","no-store");
  res.setHeader("X-Content-Type-Options","nosniff");
  try {
   String path=Optional.ofNullable(req.getPathInfo()).orElse("/"), method=req.getMethod();
   if(!Set.of("GET","POST").contains(method)) throw new Error(405,"Method not allowed");
   if(method.equals("POST")) {
    String origin=req.getHeader("Origin");
    String expected=req.getScheme()+"://"+req.getServerName()+((req.getServerPort()==80||req.getServerPort()==443)?"":":"+req.getServerPort());
    if(origin!=null&&!origin.equals(expected)) throw new Error(403,"Invalid request origin");
    if(req.getContentLengthLong()>16384) throw new Error(413,"Request too large");
   }
   JsonObject body=new JsonObject();
   if(method.equals("POST")) { char[] chars=new char[16385]; int n=req.getReader().read(chars); StringBuilder s=new StringBuilder(); while(n>0) { s.append(chars,0,n); if(s.length()>16384) throw new Error(413,"Request too large"); n=req.getReader().read(chars); } if(!s.isEmpty()) body=JsonParser.parseString(s.toString()).getAsJsonObject(); }
   try(Connection c=Db.open()) {
    Object result;
    if(path.equals("/login")&&method.equals("POST")) result=login(c,req,body);
    else if(path.equals("/register")&&method.equals("POST")) result=register(c,body);
    else {
     HttpSession session=req.getSession(false);
     if(session==null||session.getAttribute("uid")==null) throw new Error(401,"Please sign in");
     long uid=(Long)session.getAttribute("uid");
     var user=Db.one(c,"SELECT id,name,email,department,role,active FROM users WHERE id=?",uid);
     if(!Boolean.TRUE.equals(user.get("active"))) { session.invalidate(); throw new Error(403,"Your account is disabled"); }
     if(method.equals("POST")&&!Objects.equals(session.getAttribute("csrf"),req.getHeader("X-CSRF-Token"))) throw new Error(403,"Session token expired. Refresh and retry.");
     boolean admin="ADMIN".equals(user.get("role"));
     if(path.startsWith("/admin")&&!admin) throw new Error(403,"Administrator access required");
     if(path.equals("/me")&&method.equals("GET")) result=Map.of("user",user,"csrf",session.getAttribute("csrf"));
     else if(path.equals("/logout")&&method.equals("POST")) { session.invalidate();result=Map.of("ok",true); }
     else if(path.equals("/chats")&&method.equals("GET")) result=Chat.list(c,uid);
     else if(path.equals("/chat/history")&&method.equals("POST")) result=Chat.history(c,uid,body);
     else if(path.equals("/chat/send")&&method.equals("POST")) result=Chat.send(c,uid,body);
     else if(path.equals("/chat/read")&&method.equals("POST")) result=Chat.read(c,uid,body);
     else if(path.equals("/payment/history")&&method.equals("POST")) result=Payments.history(c,uid,body);
     else if(path.equals("/payment/start")&&method.equals("POST")) result=Payments.start(c,uid,body);
     else if(path.equals("/payment/finish")&&method.equals("POST")) result=Payments.finish(c,uid,body);
     else if(path.equals("/route")&&method.equals("POST")) result=Routing.quote(body);
     else if(path.equals("/matches/preview")&&method.equals("POST")) {validateTrip(body);departure(body);integer(body,"tolerance",5,180);preference(body);Map<String,Object> preview=new LinkedHashMap<>();for(String key:List.of("origin","destination","departure","preference"))preview.put(key,body.get(key).getAsString());for(String key:List.of("origin_lat","origin_lng","dest_lat","dest_lng","tolerance"))preview.put(key,body.get(key).getAsDouble());preview.put("user_id",uid);result=rankMatches(c,uid,preview);}
     else if(path.equals("/recommendations")&&method.equals("GET")) {var groups=new ArrayList<Object>();for(var request:Db.query(c,"SELECT * FROM ride_requests WHERE user_id=? AND status='OPEN' AND departure>NOW() ORDER BY departure LIMIT 20",uid)){groups.add(Map.of("request",request,"recommendations",matches(c,uid,num(request,"id"))));}result=Map.of("groups",groups,"refresh_seconds",5);}
     else if(path.equals("/rides")&&method.equals("GET")) result=Db.query(c,"SELECT r.*,u.name driver,u.department FROM rides r JOIN users u ON u.id=r.driver_id WHERE r.status='OPEN' AND r.departure>NOW() AND r.available_seats>0 AND u.active=1 ORDER BY r.departure LIMIT 200");
     else if(path.equals("/rides")&&method.equals("POST")) result=createRide(c,uid,body);
     else if(path.equals("/requests")&&method.equals("POST")) result=createRequest(c,uid,body);
     else if(path.equals("/mine")&&method.equals("GET")) result=Map.of("offers",Db.query(c,"SELECT * FROM rides WHERE driver_id=? ORDER BY departure DESC",uid),"requests",Db.query(c,"SELECT * FROM ride_requests WHERE user_id=? ORDER BY departure DESC",uid),"bookings",Db.query(c,"SELECT b.id,b.status,b.ride_id,r.origin,r.destination,r.departure,r.price,u.name driver,f.rating,(SELECT p.status FROM demo_payments p WHERE p.booking_id=b.id ORDER BY p.id DESC LIMIT 1) payment_status FROM bookings b JOIN rides r ON b.ride_id=r.id JOIN users u ON r.driver_id=u.id LEFT JOIN feedback f ON f.booking_id=b.id WHERE b.passenger_id=? ORDER BY r.departure DESC",uid));
     else if(path.equals("/passengers")&&method.equals("POST")) { long rideId=integer(body,"ride_id",1,Long.MAX_VALUE); var ride=Db.one(c,"SELECT driver_id FROM rides WHERE id=?",rideId); if(num(ride,"driver_id")!=uid&&!admin) throw new Error(403,"Only the driver can view passengers"); result=Db.query(c,"SELECT u.name,u.email,u.department,b.status FROM bookings b JOIN users u ON u.id=b.passenger_id WHERE b.ride_id=? AND b.status<>'CANCELLED'",rideId); }
     else if(path.equals("/matches")&&method.equals("POST")) result=matches(c,uid,integer(body,"request_id",1,Long.MAX_VALUE));
     else if(path.equals("/book")&&method.equals("POST")) result=book(c,uid,body);
     else if(path.equals("/booking/cancel")&&method.equals("POST")) result=cancelBooking(c,uid,integer(body,"id",1,Long.MAX_VALUE));
     else if(path.equals("/ride/status")&&method.equals("POST")) result=rideStatus(c,uid,admin,body);
     else if(path.equals("/request/cancel")&&method.equals("POST")) { long n=Db.update(c,"UPDATE ride_requests SET status='CANCELLED' WHERE id=? AND user_id=? AND status='OPEN'",integer(body,"id",1,Long.MAX_VALUE),uid); if(n==0) throw new Error(409,"Request is no longer open"); result=Map.of("ok",true); }
     else if(path.equals("/feedback")&&method.equals("POST")) result=feedback(c,uid,body);
     else if(path.equals("/analytics")&&method.equals("GET")) result=analytics(c,uid,admin);
     else if(path.equals("/admin/users")&&method.equals("GET")) result=Db.query(c,"SELECT id,name,email,department,role,active,created_at FROM users ORDER BY id");
     else if(path.equals("/admin/users")&&method.equals("POST")) { long id=integer(body,"id",1,Long.MAX_VALUE); if(id==uid) throw new Error(400,"You cannot disable your own account"); if(Db.update(c,"UPDATE users SET active=? WHERE id=? AND role<>'ADMIN'",body.get("active").getAsBoolean(),id)==0) throw new Error(400,"Only employee accounts can be changed"); audit(c,uid,"Changed employee "+id);result=Map.of("ok",true); }
     else if(path.equals("/admin/settings")&&method.equals("GET")) result=Db.one(c,"SELECT * FROM settings WHERE id=1");
     else if(path.equals("/admin/settings")&&method.equals("POST")) { Db.update(c,"UPDATE settings SET max_route_km=?,co2_kg_per_km=?,solo_cost_per_km=? WHERE id=1",number(body,"max_route_km",0.1,30),number(body,"co2_kg_per_km",0.01,1),number(body,"solo_cost_per_km",1,100));audit(c,uid,"Updated matching and impact settings");result=Map.of("ok",true); }
     else if(path.equals("/admin/rides")&&method.equals("GET")) result=Db.query(c,"SELECT r.*,u.name driver FROM rides r JOIN users u ON u.id=r.driver_id ORDER BY departure DESC LIMIT 500");
     else if(path.equals("/admin/health")&&method.equals("GET")) { Object ml; try { ml=MlClient.call("/health",Map.of()); } catch(Error e) { ml=Map.of("status","offline"); } result=Map.of("database","connected","ml",ml,"audit",Db.query(c,"SELECT a.*,u.name FROM audit_log a LEFT JOIN users u ON a.user_id=u.id ORDER BY a.id DESC LIMIT 20")); }
     else if(path.equals("/admin/retrain")&&method.equals("POST")) {result=retrain(c);audit(c,uid,"Retrained recommendation model");}
     else if(path.equals("/admin/report")&&method.equals("GET")) {res.setContentType("text/csv; charset=UTF-8");res.setHeader("Content-Disposition","attachment; filename=smartride-report.csv"); var rows=Db.query(c,"SELECT r.id,r.origin,r.destination,r.departure,r.status,r.distance_km,r.seats,(r.seats-r.available_seats) passengers,r.price FROM rides r ORDER BY departure");var w=res.getWriter();w.println("id,origin,destination,departure,status,distance_km,seats,passengers,price");for(var row:rows) w.println(String.join(",",row.values().stream().map(Api::csv).toList()));return;}
     else throw new Error(404,"Endpoint not found");
    }
    res.getWriter().print(JSON.toJson(result));
   }
  } catch(Error e) {res.setStatus(e.status);res.getWriter().print(JSON.toJson(Map.of("error",e.getMessage())));}
    catch(SQLIntegrityConstraintViolationException e) {res.setStatus(409);res.getWriter().print(JSON.toJson(Map.of("error","This record already exists or conflicts with another record.")));}
    catch(IllegalArgumentException|IllegalStateException|NullPointerException e) {res.setStatus(400);res.getWriter().print(JSON.toJson(Map.of("error","Invalid input. Check the form fields.")));}
    catch(Exception e) {getServletContext().log("API failure",e);res.setStatus(500);res.getWriter().print(JSON.toJson(Map.of("error","Server error. Check the application logs.")));}
 }
 private Object login(Connection c,HttpServletRequest req,JsonObject b)throws SQLException {
  String email=text(b,"email",190).toLowerCase(Locale.ROOT), key=req.getRemoteAddr();
  synchronized(ATTEMPTS) {long now=System.currentTimeMillis();ATTEMPTS.entrySet().removeIf(e->now-e.getValue()[0]>600000);long[] a=ATTEMPTS.computeIfAbsent(key,k->new long[]{now,0});if(++a[1]>30) throw new Error(429,"Too many sign-in attempts. Retry in 10 minutes.");}
  var rows=Db.query(c,"SELECT * FROM users WHERE email=?",email);
  if(rows.isEmpty()||!Passwords.verify(text(b,"password",128),(String)rows.get(0).get("password_hash"))) throw new Error(401,"Incorrect email or password");
  var u=rows.get(0);if(!Boolean.TRUE.equals(u.get("active")))throw new Error(403,"Your account is disabled");
  if(req.getSession(false)!=null)req.getSession(false).invalidate();var s=req.getSession(true);s.setAttribute("uid",((Number)u.get("id")).longValue());s.setAttribute("csrf",UUID.randomUUID().toString());s.setMaxInactiveInterval(3600);audit(c,((Number)u.get("id")).longValue(),"Signed in");
  return Map.of("ok",true,"csrf",s.getAttribute("csrf"));
 }
 private Object register(Connection c,JsonObject b)throws SQLException {
  String email=text(b,"email",190).toLowerCase(Locale.ROOT),password=text(b,"password",128);
  if(!email.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"))throw new Error(400,"Enter a valid email");
  if(password.length()<10)throw new Error(400,"Use at least 10 characters for your password");
  long id=Db.update(c,"INSERT INTO users(name,email,password_hash,department) VALUES(?,?,?,?)",text(b,"name",100),email,Passwords.hash(password),text(b,"department",100));audit(c,id,"Registered");return Map.of("id",id);
 }
 private Object createRide(Connection c,long uid,JsonObject b)throws SQLException {
  validateTrip(b);long seats=integer(b,"seats",1,7);departure(b);var route=Routing.quote(b);
  long id=Db.update(c,"INSERT INTO rides(driver_id,origin,destination,origin_lat,origin_lng,dest_lat,dest_lng,departure,seats,available_seats,price,distance_km,preference) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",uid,text(b,"origin",120),text(b,"destination",120),number(b,"origin_lat",-90,90),number(b,"origin_lng",-180,180),number(b,"dest_lat",-90,90),number(b,"dest_lng",-180,180),departure(b),seats,seats,route.get("price").getAsDouble(),route.get("distance_km").getAsDouble(),preference(b));audit(c,uid,"Offered ride "+id);return Map.of("id",id);
 }
 private Object createRequest(Connection c,long uid,JsonObject b)throws SQLException {
  validateTrip(b);long id=Db.update(c,"INSERT INTO ride_requests(user_id,origin,destination,origin_lat,origin_lng,dest_lat,dest_lng,departure,tolerance,preference) VALUES(?,?,?,?,?,?,?,?,?,?)",uid,text(b,"origin",120),text(b,"destination",120),number(b,"origin_lat",-90,90),number(b,"origin_lng",-180,180),number(b,"dest_lat",-90,90),number(b,"dest_lng",-180,180),departure(b),integer(b,"tolerance",5,180),preference(b));return Map.of("id",id);
 }
 private Object matches(Connection c,long uid,long id)throws SQLException {
  var request=Db.one(c,"SELECT * FROM ride_requests WHERE id=? AND user_id=? AND status='OPEN' AND departure>NOW()",id,uid);
  var result=rankMatches(c,uid,request);
  for(var el:result.getAsJsonArray("matches")) {var m=el.getAsJsonObject();Db.update(c,"INSERT INTO match_history(request_id,ride_id,score,features,model_version) VALUES(?,?,?,?,?) ON DUPLICATE KEY UPDATE score=VALUES(score),features=VALUES(features),model_version=VALUES(model_version)",id,m.get("id").getAsLong(),m.get("score").getAsDouble(),m.get("features").toString(),result.get("model_version").getAsString());}
  return result;
 }
 private JsonObject rankMatches(Connection c,long uid,Map<String,Object> request)throws SQLException {
  var settings=Db.one(c,"SELECT * FROM settings WHERE id=1");
  var candidates=Db.query(c,"SELECT r.*,u.name driver,u.department,COALESCE((SELECT AVG(f.rating) FROM feedback f JOIN bookings b ON f.booking_id=b.id JOIN rides rr ON b.ride_id=rr.id WHERE rr.driver_id=u.id),0) rating FROM rides r JOIN users u ON r.driver_id=u.id WHERE r.status='OPEN' AND r.available_seats>0 AND r.departure>NOW() AND r.driver_id<>? AND u.active=1 AND ABS(TIMESTAMPDIFF(MINUTE,r.departure,?))<=? AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.ride_id=r.id AND b.passenger_id=? AND b.status<>'CANCELLED')",uid,request.get("departure"),request.get("tolerance"),uid);
  var result=MlClient.call("/recommend",Map.of("request",request,"rides",candidates,"settings",settings)).getAsJsonObject();
  var counts=Db.one(c,"SELECT COUNT(*) upcoming_offers,COALESCE(SUM(r.driver_id=?),0) own_offers,COALESCE(SUM(r.driver_id<>? AND r.available_seats>0 AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.ride_id=r.id AND b.passenger_id=? AND b.status<>'CANCELLED')),0) available_other_offers FROM rides r JOIN users u ON u.id=r.driver_id WHERE r.status='OPEN' AND r.departure>NOW() AND u.active=1",uid,uid,uid);
  String reason="MATCHES_FOUND",title="Compatible rides found",message="Choose a ride to reserve a seat.";
  if(result.getAsJsonArray("matches").isEmpty()) {
   if(num(counts,"upcoming_offers")==0){reason="NO_UPCOMING_OFFERS";title="No upcoming ride offers";message="Your request is saved separately from a driver's offer. Another employee must publish a future ride before AI can recommend it. Past rides are excluded.";}
   else if(num(counts,"upcoming_offers")==num(counts,"own_offers")){reason="ONLY_OWN_OFFERS";title="The upcoming offers are your own";message="You cannot be the driver and passenger on the same ride. Another employee needs to offer a compatible ride. To test your existing offers, sign in as a different employee and request the same route and departure time.";}
   else if(num(counts,"available_other_offers")==0){reason="NO_AVAILABLE_SEATS";title="No unbooked seats from other drivers";message="Other employees' upcoming rides are full or already booked by you. AI will refresh when an available seat appears.";}
   else if(candidates.isEmpty()){reason="TIME_MISMATCH";title="No offers within your departure window";message="Available rides from other employees do not depart within "+request.get("tolerance")+" minutes of your requested time. Browse upcoming rides to compare dates and times, or save a request with a wider window.";}
   else {reason="ROUTE_MISMATCH";title="The available rides are too far from your route";message="There are "+candidates.size()+" offers in your time window, but no ride has both pickup and destination within "+settings.get("max_route_km")+" km of yours. Check the map points; changing a location label alone does not move its coordinates.";}
  }
  counts.put("time_compatible_offers",candidates.size());counts.put("max_route_km",settings.get("max_route_km"));counts.put("reason",reason);counts.put("title",title);counts.put("message",message);
  result.add("diagnostics",JSON.toJsonTree(counts));return result;
 }
 private Object book(Connection c,long uid,JsonObject b)throws SQLException {
  long rideId=integer(b,"ride_id",1,Long.MAX_VALUE);Long requestId=b.has("request_id")&&!b.get("request_id").isJsonNull()?integer(b,"request_id",1,Long.MAX_VALUE):null;
  c.setAutoCommit(false);
  try {
   var r=Db.one(c,"SELECT r.*,u.active driver_active FROM rides r JOIN users u ON u.id=r.driver_id WHERE r.id=? FOR UPDATE",rideId);
   if(!"OPEN".equals(r.get("status"))||num(r,"available_seats")<1||!Boolean.TRUE.equals(r.get("driver_active"))||!future(r.get("departure")))throw new Error(409,"This ride is no longer available");
   if(num(r,"driver_id")==uid)throw new Error(400,"You cannot book your own ride");
   if(requestId!=null) {Db.one(c,"SELECT id FROM ride_requests WHERE id=? AND user_id=? AND status='OPEN' AND departure>NOW() FOR UPDATE",requestId,uid);Db.one(c,"SELECT id FROM match_history WHERE request_id=? AND ride_id=?",requestId,rideId);}
   var old=Db.query(c,"SELECT id,status FROM bookings WHERE ride_id=? AND passenger_id=?",rideId,uid);long id;
   if(!old.isEmpty()) {if(!"CANCELLED".equals(old.get(0).get("status")))throw new Error(409,"You already booked this ride");id=num(old.get(0),"id");Db.update(c,"UPDATE bookings SET status='CONFIRMED',request_id=? WHERE id=?",requestId,id);}
   else id=Db.update(c,"INSERT INTO bookings(ride_id,passenger_id,request_id) VALUES(?,?,?)",rideId,uid,requestId);
   Db.update(c,"UPDATE rides SET available_seats=available_seats-1 WHERE id=?",rideId);
   if(requestId!=null)Db.update(c,"UPDATE ride_requests SET status='BOOKED' WHERE id=?",requestId);
   audit(c,uid,"Booked ride "+rideId);c.commit();return Map.of("id",id);
  } catch(Exception e) {c.rollback();throw e;} finally {c.setAutoCommit(true);}
 }
 private Object cancelBooking(Connection c,long uid,long id)throws SQLException {
  c.setAutoCommit(false);try {
   var first=Db.one(c,"SELECT ride_id FROM bookings WHERE id=? AND passenger_id=?",id,uid);
   var ride=Db.one(c,"SELECT status FROM rides WHERE id=? FOR UPDATE",first.get("ride_id"));
   var b=Db.one(c,"SELECT * FROM bookings WHERE id=? AND passenger_id=? FOR UPDATE",id,uid);
   if(!"CONFIRMED".equals(b.get("status"))||!"OPEN".equals(ride.get("status")))throw new Error(409,"Booking cannot be cancelled");
   Payments.cancel(c,id);Db.update(c,"UPDATE bookings SET status='CANCELLED' WHERE id=?",id);Db.update(c,"UPDATE rides SET available_seats=available_seats+1 WHERE id=?",b.get("ride_id"));
   if(b.get("request_id")!=null)Db.update(c,"UPDATE ride_requests SET status='OPEN' WHERE id=?",b.get("request_id"));c.commit();return Map.of("ok",true);
  }catch(Exception e){c.rollback();throw e;}finally{c.setAutoCommit(true);}
 }
 private Object rideStatus(Connection c,long uid,boolean admin,JsonObject b)throws SQLException {
  long id=integer(b,"id",1,Long.MAX_VALUE);String status=text(b,"status",20);if(!Set.of("COMPLETED","CANCELLED").contains(status))throw new Error(400,"Invalid status");
  c.setAutoCommit(false);try {
   var r=Db.one(c,"SELECT * FROM rides WHERE id=? FOR UPDATE",id);if(num(r,"driver_id")!=uid&&!admin)throw new Error(403,"Only the driver can change this ride");
   if(!"OPEN".equals(r.get("status")))throw new Error(409,"Ride is already closed");
   if(status.equals("COMPLETED")&&future(r.get("departure")))throw new Error(400,"Complete a ride only after its departure time");
   if(status.equals("CANCELLED")) {Payments.cancelRide(c,id);Db.update(c,"UPDATE ride_requests SET status='OPEN' WHERE id IN (SELECT request_id FROM bookings WHERE ride_id=? AND status='CONFIRMED')",id);}
   Db.update(c,"UPDATE rides SET status=?,available_seats=IF(?='CANCELLED',seats,available_seats) WHERE id=?",status,status,id);
   Db.update(c,"UPDATE bookings SET status=? WHERE ride_id=? AND status='CONFIRMED'",status,id);audit(c,uid,status+" ride "+id);c.commit();return Map.of("ok",true);
  }catch(Exception e){c.rollback();throw e;}finally{c.setAutoCommit(true);}
 }
 private Object feedback(Connection c,long uid,JsonObject b)throws SQLException {
  long id=integer(b,"booking_id",1,Long.MAX_VALUE);Db.one(c,"SELECT id FROM bookings WHERE id=? AND passenger_id=? AND status='COMPLETED'",id,uid);
  Db.update(c,"INSERT INTO feedback(booking_id,rating,comment) VALUES(?,?,?)",id,integer(b,"rating",1,5),b.has("comment")?optionalText(b,"comment",500):"");
  Object training;try{training=retrain(c);}catch(Error e){training=Map.of("status","pending","message","Feedback saved; model service unavailable");}
  return Map.of("ok",true,"training",training);
 }
 private Object retrain(Connection c)throws SQLException {
  return MlClient.call("/train",Map.of("samples",Db.query(c,"SELECT m.features,f.rating FROM feedback f JOIN bookings b ON b.id=f.booking_id JOIN match_history m ON m.request_id=b.request_id AND m.ride_id=b.ride_id ORDER BY f.id")));
 }
 private Object analytics(Connection c,long uid,boolean admin)throws SQLException {
  String scope=admin?"":" AND (r.driver_id="+uid+" OR EXISTS(SELECT 1 FROM bookings bx WHERE bx.ride_id=r.id AND bx.passenger_id="+uid+" AND bx.status='COMPLETED'))";
  var totals=Db.one(c,"SELECT COUNT(*) completed_rides,COALESCE(SUM(r.seats-r.available_seats),0) shared_seats,COALESCE(SUM(r.distance_km*(r.seats-r.available_seats)),0) passenger_km,COALESCE(SUM(r.distance_km*(r.seats-r.available_seats)*s.co2_kg_per_km),0) co2_saved,COALESCE(SUM(GREATEST(0,r.distance_km*s.solo_cost_per_km-r.price)*(r.seats-r.available_seats)),0) cost_saved,COALESCE(100*SUM(r.seats-r.available_seats)/NULLIF(SUM(r.seats),0),0) occupancy FROM rides r CROSS JOIN settings s WHERE r.status='COMPLETED'"+scope);
  var trends=Db.query(c,"SELECT DATE(r.departure) day,COUNT(*) rides,SUM(r.seats-r.available_seats) passengers FROM rides r WHERE r.status='COMPLETED' AND r.departure>=DATE_SUB(CURDATE(),INTERVAL 13 DAY)"+scope+" GROUP BY DATE(r.departure) ORDER BY day");
  var routes=Db.query(c,"SELECT r.origin,r.destination,COUNT(*) rides FROM rides r WHERE r.status='COMPLETED'"+scope+" GROUP BY r.origin,r.destination ORDER BY rides DESC LIMIT 5");
  Object forecast;if(admin) {try{forecast=MlClient.call("/forecast",Map.of("history",Db.query(c,"SELECT DATE(departure) day,HOUR(departure) hour,COUNT(*) demand FROM ride_requests WHERE departure>=DATE_SUB(CURDATE(),INTERVAL 90 DAY) AND departure<CURDATE() GROUP BY DATE(departure),HOUR(departure) ORDER BY day,hour")));}catch(Error e){forecast=Map.of("status","unavailable","predictions",List.of());}}else forecast=Map.of("status","admin_only","predictions",List.of());
  return Map.of("totals",totals,"trends",trends,"routes",routes,"forecast",forecast,"scope",admin?"Organisation":"Rides you participated in","settings",Db.one(c,"SELECT * FROM settings WHERE id=1"));
 }
 static String text(JsonObject b,String k,int max) {String v=optionalText(b,k,max);if(v.isBlank())throw new Error(400,k+" is required");return v;}
 static String optionalText(JsonObject b,String k,int max) {if(!b.has(k)||b.get(k).isJsonNull()||!b.get(k).isJsonPrimitive())throw new Error(400,k+" is required");String v=b.get(k).getAsString().strip();if(v.length()>max)throw new Error(400,k+" is too long");return v;}
 static double number(JsonObject b,String k,double min,double max) {double v=b.get(k).getAsDouble();if(!Double.isFinite(v)||v<min||v>max)throw new Error(400,k+" must be between "+min+" and "+max);return v;}
 static long integer(JsonObject b,String k,long min,long max) {double v=number(b,k,min,max);if(v!=Math.floor(v))throw new Error(400,k+" must be an integer");return (long)v;}
 static String preference(JsonObject b) {String p=text(b,"preference",10);if(!Set.of("quiet","chatty","any").contains(p))throw new Error(400,"Invalid preference");return p;}
 static Timestamp departure(JsonObject b) {LocalDateTime t=LocalDateTime.parse(text(b,"departure",25).replace(' ','T'));if(t.isBefore(LocalDateTime.now())||t.isAfter(LocalDateTime.now().plusDays(90)))throw new Error(400,"Choose a departure within the next 90 days");return Timestamp.valueOf(t);}
 static void validateTrip(JsonObject b) {if(text(b,"origin",120).equalsIgnoreCase(text(b,"destination",120)))throw new Error(400,"Choose different pickup and destination locations");double a=number(b,"origin_lat",-90,90),o=number(b,"origin_lng",-180,180),d=number(b,"dest_lat",-90,90),l=number(b,"dest_lng",-180,180);if(Math.abs(a-d)+Math.abs(o-l)<0.0001)throw new Error(400,"Pickup and destination coordinates must differ");}
 static long num(Map<String,Object> m,String k) {return ((Number)m.get(k)).longValue();}
 static boolean future(Object value) {return LocalDateTime.parse(value.toString().replace(' ','T')).isAfter(LocalDateTime.now());}
 static void audit(Connection c,long uid,String action)throws SQLException {Db.update(c,"INSERT INTO audit_log(user_id,action) VALUES(?,?)",uid,action);}
 static String csv(Object v) {String s=Objects.toString(v,"");if(s.matches("^[=+@\\-\\t\\r].*"))s="'"+s;return "\""+s.replace("\"","\"\"")+"\"";}
}
