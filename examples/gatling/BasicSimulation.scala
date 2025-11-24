package computerdatabase

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

/**
 * Exemple de simulation Gatling pour tester l'API ProjetIA
 *
 * Ce script simule des utilisateurs generant des tests avec l'API
 */
class BasicSimulation extends Simulation {

  // Configuration du protocole HTTP
  val httpProtocol = http
    .baseUrl("http://localhost:8000")
    .acceptHeader("application/json")
    .contentTypeHeader("application/json")
    .userAgentHeader("Gatling Performance Test")

  // Scenario de test : Generation de tests
  val scn = scenario("API Test Generation")
    .exec(
      http("Health Check")
        .get("/health")
        .check(status.is(200))
    )
    .pause(1)
    .exec(
      http("Generate Test Preview")
        .post("/generate-test-preview")
        .body(StringBody("""{
          "code": "public class Calculator { public int add(int a, int b) { return a + b; } }",
          "test_type": "unit",
          "language": "java",
          "provider": "gemini"
        }"""))
        .check(status.is(200))
        .check(jsonPath("$.result").exists)
    )
    .pause(2)
    .exec(
      http("List Test Cases")
        .get("/test-cases?limit=10")
        .check(status.is(200))
    )

  // Injection de charge : 10 utilisateurs en 10 secondes
  setUp(
    scn.inject(
      rampUsers(10).during(10.seconds)
    ).protocols(httpProtocol)
  ).assertions(
    global.responseTime.max.lt(5000),  // Temps de reponse max < 5s
    global.successfulRequests.percent.gt(95)  // Taux de succes > 95%
  )
}
