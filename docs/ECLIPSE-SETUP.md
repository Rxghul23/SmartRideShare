# Eclipse IDE setup

Use Eclipse IDE for Enterprise Java and Web Developers with Maven integration. The application files are already created at `Z:\CAO-DA`; opening a JSP directly in a browser will not run the server.

1. Open Eclipse. Choose a workspace outside the project, for example `Z:\eclipse-workspace`.
2. In **Window → Preferences → Java → Installed JREs**, choose **Add → Standard VM**. Set the JRE home to `Z:\CAO-DA\.tools\jdk-21.0.8+9` and make it the default.
3. Under **Java → Installed JREs → Execution Environments**, associate **JavaSE-17** with that JDK. The project targets Java 17 and runs on JDK 21.
4. Choose **File → Import → Maven → Existing Maven Projects**. Select `Z:\CAO-DA`, check `pom.xml`, and finish. The supplied project name is **SmartRideShare**. If Eclipse names it `smartride`, rename it to `SmartRideShare` so the supplied launch configurations resolve.
5. Right-click the project and choose **Maven → Update Project**. Allow Maven to resolve the dependencies.
6. Choose **Run → External Tools → External Tools Configurations → Program → SmartRide Build**, then Run. This compiles, tests, packages, and copies the WAR to the supplied Tomcat.
7. Run the **SmartRide Start** external-tool configuration. It starts MySQL, the Python service, and Tomcat. Open `http://localhost:8080/smartride/`.

You can also run the root START-SMARTRIDE.cmd file while editing source in Eclipse. After edits, run SmartRide Build and allow Tomcat to redeploy. Restarting the Python service is required after changes to its source.

## Optional: manage Tomcat in Eclipse's Servers view

The included launcher is the shortest working path. If you prefer Eclipse's Tomcat server adapter:

1. Stop the existing project Tomcat before using port 8080 in Eclipse.
2. Add **Apache → Tomcat v10.1 Server** in Servers. Set its installation to `Z:\CAO-DA\.tools\apache-tomcat-10.1.44` and select the bundled JDK.
3. Add the Maven WAR project. If no web module appears, use Eclipse's m2e-wtp integration and update the Maven project.
4. In the server launch configuration's Environment tab, add `DB_URL`, `DB_USER`, `DB_PASSWORD`, `ML_URL`, and `ML_SERVICE_KEY`. Values come from `scripts/env.ps1` and your local `.local-config.json`.
5. Set VM arguments to include `-Duser.timezone=Asia/Kolkata`. Keep MySQL on 3307 and Python on 5001 running. Do not run two Tomcat instances on the same port.

## Logs and common fixes

| Symptom | Action |
| --- | --- |
| System `java` fails | Use the bundled JDK; the launcher already does this. |
| Port already in use | Stop this project's prior instance, or identify the other service before changing a port. |
| MySQL connection error | Check `tmp/mysql-error.log`, port 3307, and local config. Do not change the separate MySQL80 service. |
| Recommendation service unavailable | Check `tmp/ml-error.log`, `PYTHONPATH`, and `ML_SERVICE_KEY`. |
| Compilation error in Eclipse only | Set JavaSE-17 to the bundled JDK and run Maven Update Project. |
| Old screen after rebuild | Wait for Tomcat redeployment, refresh, and sign in again. |
| Localhost loads slowly | Use `http://127.0.0.1:8080/smartride/` consistently. |

Official references: [Tomcat 10.1 documentation](https://tomcat.apache.org/tomcat-10.1-doc/), [Eclipse IDE packages](https://www.eclipse.org/downloads/packages/), [Maven WAR plugin](https://maven.apache.org/plugins/maven-war-plugin/).
