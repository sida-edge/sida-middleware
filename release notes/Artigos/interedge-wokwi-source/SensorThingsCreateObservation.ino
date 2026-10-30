/**
 * Module       : hdei : InterEdge 
 * Name         : SensorThingsCreateObservation.ino
 * Description  : In this file we have called the localhost for 
 * SensorThings API Create Observation function to 
 * store the temperature data in the cloud.
 * We read the temperature data from the temperature sensor using the ESP32 controller.
 * The ReadSensorData() method reads the temperature from the sensor. This method is used 
 * from the SOSInsertObservation.ino.
 * The sensorThingsCreateObservation() method calls the Observations function
 * of the SensorThings API.
 * See the description of the class on top of the class
 * declaration and the description of the methods on top of
 * each method
 * Project      : InterEdge - Hierarchical Decentralized Edge Interoperability
 *
 * @author : Tanzima Azad <tanzima.azad@griffithuni.edu.au>, GU
 *         Creation     : Version: 1.0  Date: May 03, 2024
 *         Language     : C++
 *         copyright    : (c) 2024 Griffith University
 *         ----------------------------------------------------------------------------
 */


/** 
 * This variable specifies the URL for the local 
 * SensorThings API web application service. 
 * Accessing localhost via Wokwi requires a membership, and 
 * the URL must use "host.wokwi.internal" instead of "localhost".
 */
const String STCOurl = "http://host.wokwi.internal:8080/52n-sensorthings-webapp/Observations";

int STCOhourValue = 1; // Initial hour value

int STCOmonthValue = 11; // Initial month value

int STCOdayValue = 1; // Initial day value

int STCOhttpResponseCode; // response code
String STCOpayload; // response string from the server

/** 
 * To perform a SensorThings API CreateObservation operation, 
 * a JSON data request is required to be sent.
*/
String STCOjsonData = "{"
  "\"phenomenonTime\": \"2020-" + String(STCOmonthValue) + "-" + String(STCOdayValue) + "T" + String(STCOhourValue) + ":57:53.00+02:00\","
  "\"resultTime\": \"2020-" + String(STCOmonthValue) + "-" + String(STCOdayValue) + "T" + String(STCOhourValue) + ":57:53.00+02:00\","
  "\"result\": 16.4,"
  "\"Datastream\": {"
    "\"@iot.id\": \"thermometer_readings_102\""
  "}"
"}";

HTTPClient STCOhttp; // Http Client to send the request and get response back

/**
* The sensorThingsCreateObservation method connects to a WiFi network and 
* sends a JSON data request to a SensorThings API server to 
* create an observation. It constructs an HTTP POST request with JSON data
* that includes the phenomenon time, result time, result, and datastream ID. 
* The method sends the request, retrieves the server's response, and prints the 
* HTTP response code and payload to the serial monitor. It also updates the timestamp 
* values to simulate continuous observation submissions to record response latency
* for our experiment.
*/
void sensorThingsCreateObservation() {

  WiFi.begin(ssid, password); // begin Wi-Fi with ssid and password
  Serial.print("Connecting to WiFi");
  /*while (WiFi.status() != WL_CONNECTED) {
      delay(1500);
      Serial.print(".");
  }*/

  if(WiFi.status() == WL_CONNECTED) {  // check if connected to Wi-Fi
  
    STCOhttp.begin(STCOurl);
    STCOhttp.addHeader("Content-Type", "application/json"); // Set Content-Type header

    for(int i = 0; i <1; i++) {
      // Send HTTP POST request

      STCOjsonData = "{"
        "\"phenomenonTime\": \"2020-" + String(STCOmonthValue) + "-" + String(STCOdayValue) + "T" + String(STCOhourValue) + ":57:53.00+02:00\","
        "\"resultTime\": \"2020-" + String(STCOmonthValue) + "-" + String(STCOdayValue) + "T" + String(STCOhourValue) + ":57:53.00+02:00\","
        "\"result\": "+ ReadSensorData() +","
        "\"Datastream\": {"
        "\"@iot.id\": \"thermometer_readings_102\""
        "}"
      "}";

      STCOhttpResponseCode = STCOhttp.POST(STCOjsonData); // http post
      if (STCOhttpResponseCode > 0) { // success response
        Serial.print("HTTP ");
        Serial.println(STCOhttpResponseCode);
        STCOpayload = STCOhttp.getString();
        Serial.println();
        Serial.println(STCOpayload);
      }
      else { // error response
        Serial.print("Error code: ");
        Serial.println(STCOhttpResponseCode);
        Serial.println(":-(");
      }

      STCOhourValue++; // hour value for multiple value to record response latency
      if(STCOhourValue == 23) {
        STCOdayValue++;
        STCOhourValue = 1;
      }
      if(STCOdayValue == 28) {
        STCOmonthValue++;
        STCOdayValue = 1;
        STCOhourValue = 1;
      }
    }
  }
}