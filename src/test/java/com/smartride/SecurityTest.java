package com.smartride;
import com.google.gson.JsonParser;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class SecurityTest {
 @Test void passwordHashesAreSaltedAndVerify() {
  String a=Passwords.hash("correct horse battery"), b=Passwords.hash("correct horse battery");
  assertNotEquals(a,b); assertTrue(Passwords.verify("correct horse battery",a));
  assertFalse(Passwords.verify("wrong",a)); assertFalse(Passwords.verify("x","malformed"));
 }
 @Test void rejectFractionalSeatsAndNonFiniteNumbers() {
  assertThrows(Api.Error.class,()->Api.integer(JsonParser.parseString("{\"seats\":1.5}").getAsJsonObject(),"seats",1,7));
  assertThrows(Api.Error.class,()->Api.number(JsonParser.parseString("{\"lat\":\"NaN\"}").getAsJsonObject(),"lat",-90,90));
 }
 @Test void csvNeutralizesFormulaAndQuotes() {
  assertEquals("\"'=1+1\"",Api.csv("=1+1"));
  assertEquals("\"a\"\"b\"",Api.csv("a\"b"));
 }
}
