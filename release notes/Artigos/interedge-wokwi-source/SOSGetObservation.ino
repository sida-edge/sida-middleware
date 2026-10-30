/**
 * Module       : hdei : InterEdge 
 * Name         : SOSGetObservation.ino
 * Description  : In this file we have called the localhost for 
 * Sensor Observation Service (SOS) Get Observation function to 
 * retrive the previously store temperature data from the cloud.
 * The sosGetObservation() method calls the Get Observation function
 * of the SOS.
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
 * SOS web application service. 
 * Accessing localhost via Wokwi requires a membership, and 
 * the URL must use "host.wokwi.internal" instead of "localhost".
 */
const String sosGOurl = "http://host.wokwi.internal:8080/52n-sos-webapp/service";

int sosGOhttpResponseCode; // response code
String sosGOpayload; // response string from the server

/** 
 * To perform a SOS GetObservation operation, a XML data request is required to be sent.
*/
String sosGOxmlData = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                      "<sos:GetObservation xmlns:sos=\"http://www.opengis.net/sos/2.0\" xmlns:fes=\"http://www.opengis.net/fes/2.0\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:swe=\"http://www.opengis.net/swe/2.0\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:swes=\"http://www.opengis.net/swes/2.0\" xmlns:sosrf=\"http://www.opengis.net/sosrf/1.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" service=\"SOS\" version=\"2.0.0\" xsi:schemaLocation=\"http://www.opengis.net/sos/2.0 http://schemas.opengis.net/sos/2.0/sos.xsd\">"
                      "<sos:procedure>Thermometer_1285</sos:procedure>"
                      "<sos:offering>Thermometer_1285_offering</sos:offering>"
                      "<sos:observedProperty>air_temperature</sos:observedProperty>"
                      "<sos:temporalFilter>"
                      "    <fes:During>"
                      "        <fes:ValueReference>phenomenonTime</fes:ValueReference>"
                      "        <gml:TimePeriod gml:id=\"tp_1\">"
                      "            <gml:beginPosition>2023-03-21T09:00:00.000+02:00</gml:beginPosition>"
                      "            <gml:endPosition>2023-03-22T10:00:00.000+02:00</gml:endPosition>"
                      "        </gml:TimePeriod>"
                      "    </fes:During>"
                      "</sos:temporalFilter>"
                      "<sos:responseFormat>http://www.opengis.net/om/2.0</sos:responseFormat>"
                      "</sos:GetObservation>";

HTTPClient sosGOhttp;

/**
* The sosGetObservation method connects to a WiFi network and 
* sends an XML data request to an SOS (Sensor Observation Service) server to 
* retrieve an observation. It constructs an HTTP POST request with the appropriate 
* headers and XML data. The method sends the request, retrieves the server's response, 
* and prints the HTTP response code and payload to the serial monitor, and 
* simulates continuous retrivals in a loop to record response latency
* for our experiment.
*/
void sosGetObservation() {
  WiFi.begin(ssid, password); // begin Wi-Fi with ssid and password
  Serial.print("Connecting to WiFi");
  /*while (WiFi.status() != WL_CONNECTED) {
      delay(1500);
      Serial.print(".");
  }*/

  if(WiFi.status() == WL_CONNECTED) {  // check if connected to Wi-Fi
    sosGOhttp.begin(sosGOurl);
    sosGOhttp.addHeader("Content-Type", "application/xml"); // Set Content-Type header

    for(int i = 0; i <1; i++) {
      // Send HTTP POST request
      sosGOhttpResponseCode = sosGOhttp.POST(sosGOxmlData); // http post
      if (sosGOhttpResponseCode > 0) { // success response
        Serial.print("HTTP ");
        Serial.println(sosGOhttpResponseCode);
        sosGOpayload = sosGOhttp.getString();
        Serial.println(sosGOpayload);
      }
      else { // error response
        Serial.print("Error code: ");
        Serial.println(sosGOhttpResponseCode);
        Serial.println(":-(");
      }
    }
  }
}