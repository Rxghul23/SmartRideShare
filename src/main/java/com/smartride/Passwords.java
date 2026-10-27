package com.smartride;
import java.security.*;
import java.util.*;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
public final class Passwords {
 private Passwords() {}
 public static String hash(String password) { byte[] salt=new byte[16]; new SecureRandom().nextBytes(salt); return "210000:"+Base64.getEncoder().encodeToString(salt)+":"+Base64.getEncoder().encodeToString(derive(password,salt,210000)); }
 public static boolean verify(String password,String stored) { try { String[] p=stored.split(":"); return MessageDigest.isEqual(Base64.getDecoder().decode(p[2]),derive(password,Base64.getDecoder().decode(p[1]),Integer.parseInt(p[0]))); } catch(Exception e) { return false; } }
 private static byte[] derive(String p,byte[] salt,int iterations) { try { return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(new PBEKeySpec(p.toCharArray(),salt,iterations,256)).getEncoded(); } catch(Exception e) { throw new IllegalStateException(e); } }
}
