package com.smartride;
import jakarta.servlet.*;
import jakarta.servlet.annotation.WebFilter;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
@WebFilter(urlPatterns={"/app.js","/maps.js","/chat.js","/payments.js","/styles.css"})
public class AssetFilter implements Filter {
 public void doFilter(ServletRequest req,ServletResponse res,FilterChain chain)throws IOException,ServletException {
  ((HttpServletResponse)res).setHeader("Cache-Control","no-cache, must-revalidate");chain.doFilter(req,res);
 }
}
