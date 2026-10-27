# Smart RideShare: simple explanation and demonstration

## Start with this explanation

“Our project is Smart RideShare. It helps people travelling in the same direction share a vehicle. A driver offers empty seats, and a passenger enters where and when they want to travel. The system automatically recommends suitable rides, calculates the road distance and price, and lets the passenger book a seat. It also provides group chat, a demo payment flow and analytics.”

## Explain the complete workflow

1. **Register and sign in.** A user supplies their name, department, email and password. The dashboard opens after login. Administrators have extra account and system-management options.
2. **Offer a ride.** A driver selects pickup, destination, departure time and available seats. The map shows the driving route. Java calculates the per-seat fare as road distance multiplied by INR 5, rounded to a rupee.
3. **Request a ride.** A passenger selects their locations, departure time, time flexibility and conversation preference.
4. **Get automatic matches.** Python excludes unavailable or incompatible offers and ranks eligible ones. Saved requests refresh every five seconds while the matching screen is open and visible.
5. **Confirm a booking.** The passenger chooses a ride. MySQL records the booking and reduces available seats. A transaction ensures that two people cannot both reserve the final seat.
6. **Try demo payment.** In My journeys, open Demo payment. Select a simulated method and simulate success, failure or cancellation. A successful outcome creates a downloadable demo receipt. No card details, API keys or money are involved.
7. **Use ride chat.** The driver and booked passengers coordinate pickup. Messages persist in MySQL and refresh every three seconds while the app is active. Other users cannot access the chat.
8. **Complete or cancel.** After departure, the driver can complete the ride. Passengers can rate a completed journey. Cancelling a booking releases its seat. A previously successful simulated payment becomes simulated REFUNDED when its booking or ride is cancelled.
9. **View analytics.** The application shows completed ride activity and estimated savings, occupancy and carbon impact. Administrators can view an experimental demand forecast when enough history exists.
10. **Admin and logout.** Administrators manage users and rides, inspect service health and export reports. Logging out ends the session.

## What each technology does

| Technology | Simple explanation |
|---|---|
| HTML and CSS | Build and style the screens |
| JavaScript | Handle clicks, maps and automatic updates |
| Java, JSP and Servlets | Handle login, permissions, booking and business rules |
| MySQL | Remember users, rides, bookings, messages, feedback and demo payments |
| Python and scikit-learn | Compare and rank rides, learn from feedback and estimate demand |
| Leaflet | Display the interactive map |
| OSRM | Supply the road route, distance and travel-time estimate |
| Apache Tomcat | Run the Java application |
| Eclipse and Maven | Develop and build the Java project |

## Where is the AI?

“The AI is in the Python recommendation service. It compares pickup proximity, destination proximity, departure time, conversation preference and driver rating. It first filters unsuitable rides, then ranks the suitable ones. A similarity score works even without training data. Once at least ten valid feedback examples exist, a Random Forest model also contributes to the score.”

For a technical follow-up: the feature weights are 30%, 30%, 25%, 10% and 5%. The baseline combines 80% weighted magnitude with 20% cosine similarity. With a trained model, the final score combines 60% baseline and 40% Random Forest prediction. The displayed score measures suitability; it is not a proven probability or accuracy percentage.

## Demonstrate it to your teacher

1. Run `Z:\CAO-DA\START-SMARTRIDE.cmd` and open http://localhost:8080/smartride/.
2. Read `Z:\CAO-DA\LOCAL-LOGIN.txt` for local demo credentials. Use one normal browser window for a driver and an incognito window for a different passenger.
3. Driver: offer a new ride from **Velachery to Tidel Park**, tomorrow at **9:00 AM**, with **two seats**. Wait for the route and fare before publishing.
4. Passenger: choose the same locations and tomorrow at **9:00 AM**, then save the request. Open AI matches. The driver's compatible offer should appear on the next refresh.
5. Book one seat. Show that only one seat remains. Open My journeys and demonstrate payment success and the demo receipt.
6. Open Ride chat in both accounts. Send a pickup message and show it arrive in the other window.
7. To demonstrate failure or retry, do it before a successful payment, or use another booking. A paid attempt cannot be changed into a failed attempt.
8. To demonstrate cancellation and refund, cancel the passenger's booking. Show the seat restored and the payment history marked REFUNDED (demo).
9. Show Analytics and then sign in as an administrator to show management and service health.

Do not complete a future ride: the app intentionally blocks this. Demonstrate completion on an eligible past-departure open ride, or explain this rule and show existing completed history. Use two different users: a driver cannot match or book their own ride. Old seeded offers may already be past, so create a new offer for the demonstration.

## Questions your teacher may ask

**Why use both Java and Python?** Java manages the web workflow and transactions; Python provides the machine-learning calculations. They communicate through a private HTTP service.

**How is price calculated?** The server obtains road distance, multiplies it by INR 5 per seat and rounds it to the nearest rupee. It does not trust a price supplied by the browser.

**Does the app automatically book a ride?** No. Recommendations are automatic, but the passenger confirms the booking.

**What if there are no matches?** The screen explains reasons such as no future offers, only the user's own offers, full rides, or mismatched time and locations. It continues checking saved requests while the screen is active.

**Is this live GPS tracking?** No. The map shows selected locations and a calculated road route. Travel time excludes live traffic. Browser location can help choose a pickup point, but the app does not continuously track vehicles.

**Is Razorpay connected?** No. At the user's request, the project has a local payment simulator with no payment APIs or real charges. It demonstrates checkout, retry, receipt and refund states. A real gateway integration would be a separate extension.

**How does chat stay private?** Java checks that the current user is the driver or a booked passenger. Cancelling a passenger's booking revokes access. Closed rides are read-only for remaining authorised participants.

**What does the analytics page mean?** It summarises recorded journeys. Cost and carbon savings depend on configurable assumptions; they are estimates, not physical measurements. Demo records include synthetic data.

**What testing was performed?** The project passed 59 automated checks: 3 Java, 6 Python, 17 integration, 12 map/matching, 11 chat and 10 payment checks. Browser rendering and mobile layout were also checked. The routing test encountered a temporary external timeout before a complete successful rerun.

**How accurate is the AI?** We have tested its filtering, ranking pipeline and integration. We have not measured predictive accuracy on a real held-out commuter dataset, so we do not claim an accuracy percentage.

## Finish with this sentence

“Our main contribution is bringing automatic ride recommendations, road-based pricing, safe booking, participant chat, simulated checkout and analytics into one working application. The next step is evaluation with real consented journey data and deployment-specific improvements.”
