package com.smartride;
import com.google.gson.*;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
public final class MlClient {
 private static final HttpClient CLIENT=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
 public static JsonElement call(String path,Object payload) {
  try {
   var req=HttpRequest.newBuilder(URI.create(Db.env("ML_URL","http://127.0.0.1:5001")+path)).timeout(Duration.ofSeconds(30)).header("Content-Type","application/json").header("X-Service-Key",Db.env("ML_SERVICE_KEY","")).POST(HttpRequest.BodyPublishers.ofString(Api.JSON.toJson(payload))).build();
   var response=CLIENT.send(req,HttpResponse.BodyHandlers.ofString());
   if(response.statusCode()!=200) throw new IllegalStateException("ML status "+response.statusCode());
   return JsonParser.parseString(response.body());
  } catch(Exception e) { throw new Api.Error(503,"Recommendation service unavailable. Please retry after starting the Python service."); }
 }
}
