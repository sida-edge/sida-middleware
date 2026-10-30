/**
 * Module       : hdei : InterEdge 
 * Name         : SensorThingsReadObservation.ino
 * Description  : In this file we have called the localhost for 
 * SensorThings API Read Observation function to 
 * retrive the previously store temperature data from the cloud.
 * The sensorthingsReadObservation() method calls the Read Observation function
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
const String STROurl = "http://host.wokwi.internal:8080/52n-sensorthings-webapp/Datastreams(thermometer_readings_102)/Observations?$filter=resultTime%20ge%202020-08-17T14:00:00Z%20and%20resultTime%20le%202025-08-17T16:00:00Z";

int STROhttpResponseCode; // response code
String STROpayload; // response string from the server

/**
* The sensorthingsReadObservation method connects to a WiFi network and 
* sends a GET request to a SensorThings API server to read an observation. 
* It constructs and sends the HTTP GET request, retrieves the server's response, 
* and prints the HTTP response code and payload to the serial monitor. 
* This method does continuous data retrieval by connecting to the WiFi network and 
* making repeated requests to record response latency for our experiment.
*/
void sensorthingsReadObservation() {

  WiFi.begin(ssid, password); // begin Wi-Fi with ssid and password

  Serial.print("Connecting to WiFi");
  /*while (WiFi.status() != WL_CONNECTED) {
    delay(1500);
    Serial.print(".");
  }*/

  if(WiFi.status() == WL_CONNECTED) { // check if connected to Wi-Fi

    HTTPClient STROhttp;

    STROhttp.begin(STROurl);
    
    for(int i = 0; i <1; i++) {
      // HTTP GET request
      STROhttpResponseCode = STROhttp.GET(); // http get
      if (STROhttpResponseCode > 0) { // success response
        Serial.print("HTTP ");
        Serial.println(STROhttpResponseCode);
        STROpayload = STROhttp.getString();
        Serial.println();
        Serial.println(STROpayload);
      }
      else { // error response
        Serial.print("Error code: ");
        Serial.println(STROhttpResponseCode);
        Serial.println(":-(");
      }
    }
  }
}