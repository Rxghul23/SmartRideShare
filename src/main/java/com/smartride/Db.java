package com.smartride;

import java.sql.*;
import java.util.*;

/** Small JDBC boundary; callers own transactions for multi-row changes. */
public final class Db {
    private Db() {}
    public static Connection open() throws SQLException {
        try { Class.forName("com.mysql.cj.jdbc.Driver"); }
        catch (ClassNotFoundException e) { throw new SQLException("MySQL JDBC driver missing", e); }
        return DriverManager.getConnection(env("DB_URL", "jdbc:mysql://127.0.0.1:3307/smartride?serverTimezone=Asia/Kolkata"), env("DB_USER","smartride"), env("DB_PASSWORD", ""));
    }
    public static String env(String key, String fallback) { return System.getenv().getOrDefault(key, fallback); }
    public static List<Map<String,Object>> query(Connection c, String sql, Object... args) throws SQLException {
        try (PreparedStatement p=c.prepareStatement(sql)) {
            bind(p,args); try(ResultSet r=p.executeQuery()) {
                List<Map<String,Object>> out=new ArrayList<>();
                while(r.next()) { Map<String,Object> row=new LinkedHashMap<>(); for(int i=1;i<=r.getMetaData().getColumnCount();i++) { Object v=r.getObject(i); if(v instanceof java.sql.Timestamp) v=v.toString().substring(0,19); else if(v instanceof java.time.temporal.TemporalAccessor || v instanceof java.sql.Date) v=v.toString(); row.put(r.getMetaData().getColumnLabel(i),v); } out.add(row); }
                return out;
            }
        }
    }
    public static long update(Connection c,String sql,Object... args) throws SQLException {
        try(PreparedStatement p=c.prepareStatement(sql,Statement.RETURN_GENERATED_KEYS)) { bind(p,args); int n=p.executeUpdate(); try(ResultSet r=p.getGeneratedKeys()) { return r.next()?r.getLong(1):n; } }
    }
    private static void bind(PreparedStatement p,Object[] a) throws SQLException { for(int i=0;i<a.length;i++) p.setObject(i+1,a[i]); }
    public static Map<String,Object> one(Connection c,String sql,Object... args) throws SQLException { var rows=query(c,sql,args); if(rows.isEmpty()) throw new Api.Error(404,"Record not found"); return rows.get(0); }
}
