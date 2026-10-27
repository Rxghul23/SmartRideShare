package com.smartride;

import com.google.gson.*;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;

/** Shared, bounded road-route cache. Coordinates only are sent to the routing provider. */
public final class Routing {
 private static final HttpClient CLIENT=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
 private record Entry(long expires, JsonObject value) {}
 private static final Map<String,Entry> CACHE=new LinkedHashMap<>();
 private static long lastCall=0;
 private Routing() {}
 public static synchronized JsonObject quote(JsonObject b) {
  double lat1=Api.number(b,"origin_lat",-90,90),lon1=Api.number(b,"origin_lng",-180,180);
  double lat2=Api.number(b,"dest_lat",-90,90),lon2=Api.number(b,"dest_lng",-180,180);
  if(Math.abs(lat1-lat2)+Math.abs(lon1-lon2)<0.0001) throw new Api.Error(400,"Choose different pickup and destination points.");
  String coordinates=String.format(Locale.ROOT,"%.6f,%.6f;%.6f,%.6f",lon1,lat1,lon2,lat2);
  long now=System.currentTimeMillis();Entry cached=CACHE.get(coordinates);
  if(cached!=null && cached.expires>now) return cached.value.deepCopy();
  try {
   long delay=1000-(now-lastCall);if(delay>0)Thread.sleep(delay);
   lastCall=System.currentTimeMillis();
   String base=Db.env("ROUTING_URL","https://router.project-osrm.org");
   var req=HttpRequest.newBuilder(URI.create(base+"/route/v1/driving/"+coordinates+"?overview=full&geometries=geojson&steps=false"))
    .timeout(Duration.ofSeconds(12)).header("User-Agent","SmartRideShare-LocalProject/1.0").GET().build();
   var response=CLIENT.send(req,HttpResponse.BodyHandlers.ofString());
   if(response.statusCode()!=200)throw new IllegalStateException("Routing HTTP "+response.statusCode());
   var data=JsonParser.parseString(response.body()).getAsJsonObject();
   if(!"Ok".equals(data.get("code").getAsString())||data.getAsJsonArray("routes").isEmpty())
    throw new Api.Error(422,"No driving route found. Move the pickup or destination closer to a road.");
   for(var point:data.getAsJsonArray("waypoints")) if(point.getAsJsonObject().get("distance").getAsDouble()>2000)
    throw new Api.Error(422,"A selected point is more than 2 km from a drivable road. Choose a closer point.");
   var route=data.getAsJsonArray("routes").get(0).getAsJsonObject();
   double km=Math.max(0.1,Math.round(route.get("distance").getAsDouble()/100.0)/10.0);
   if(km>1000)throw new Api.Error(400,"Please select a commute under 1,000 km.");
   JsonObject result=new JsonObject();result.addProperty("distance_km",km);result.addProperty("price",Math.round(km*5));
   result.addProperty("rate_per_km",5);result.addProperty("duration_min",Math.max(1,Math.round(route.get("duration").getAsDouble()/60)));
   result.addProperty("source","OSRM road routing");result.addProperty("traffic_live",false);
   result.add("geometry",route.get("geometry"));
   CACHE.entrySet().removeIf(e->e.getValue().expires<System.currentTimeMillis());
   if(CACHE.size()>=256)CACHE.remove(CACHE.keySet().iterator().next());
   CACHE.put(coordinates,new Entry(System.currentTimeMillis()+600000,result.deepCopy()));return result;
  } catch(Api.Error e) {throw e;}
    catch(InterruptedException e) {Thread.currentThread().interrupt();throw new Api.Error(503,"Route calculation interrupted. Please retry.");}
    catch(Exception e) {throw new Api.Error(503,"Road routing is unavailable. Check your internet connection and retry; no estimated fare has been substituted.");}
 }
}
