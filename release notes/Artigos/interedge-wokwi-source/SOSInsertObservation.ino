/**
 * Module       : hdei : InterEdge 
 * Name         : SOSInsertObservation.ino
 * Description  : In this file we have called the localhost for 
 * Sensor Observation Service (SOS) Insert Observation function to 
 * store the temperature data in the cloud.
 * We read the temperature data from the temperature sensor using the ESP32 controller.
 * The ReadSensorData() method reads the temperature from the sensor.
 * The sosInsertObservation() method calls the Insert Observation function
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
const String sosIOurl = "http://host.wokwi.internal:8080/52n-sos-webapp/service";

int sosIOhourValue = 1; // Initial hour value

int sosIOmonthValue = 10; // Initial month value

int sosIOdayValue = 1; // Initial day value

int sosIOhttpResponseCode; // response code
String sosIOpayload; // response string from the server


/** 
 * To perform a SOS InsertObservation operation, a XML data request is required to be sent.
*/
String sosIOxmlData = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                        "<sos:InsertObservation xmlns:sos=\"http://www.opengis.net/sos/2.0\" xmlns:swes=\"http://www.opengis.net/swes/2.0\" xmlns:swe=\"http://www.opengis.net/swe/2.0\" xmlns:sml=\"http://www.opengis.net/sensorML/1.0.1\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:sams=\"http://www.opengis.net/samplingSpatial/2.0\" xmlns:sf=\"http://www.opengis.net/sampling/2.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" service=\"SOS\" version=\"2.0.0\" xsi:schemaLocation=\"http://www.opengis.net/sos/2.0 http://schemas.opengis.net/sos/2.0/sos.xsd  http://www.opengis.net/samplingSpatial/2.0 http://schemas.opengis.net/samplingSpatial/2.0/spatialSamplingFeature.xsd\">"
                        "<sos:offering>Thermometer_1285_offering</sos:offering>"
                        "<sos:observation>"
                        "    <om:OM_Observation gml:id=\"o1\">"
                        "        <om:type xlink:href=\"http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement\"/>"
                        "        <om:phenomenonTime>"
                        "            <gml:TimeInstant gml:id=\"phenomenonTime\">"
                        "                <gml:timePosition>2024-02-8T" + String(sosIOhourValue) + ":00:12.000+02:00</gml:timePosition>"
                        "            </gml:TimeInstant>"
                        "        </om:phenomenonTime>"
                        "        <om:resultTime xlink:href=\"#phenomenonTime\"/>"
                        "        <om:procedure xlink:href=\"Thermometer_1285\"/>"
                        "        <om:observedProperty xlink:href=\"air_temperature\"/>"
                        "        <om:featureOfInterest>"
                        "            <sams:SF_SpatialSamplingFeature gml:id=\"ssf_brisbane\">"
                        "                <gml:identifier codeSpace=\"\">Brisbane</gml:identifier>"
                        "                <gml:name>Brisbane</gml:name>"
                        "                <sf:type xlink:href=\"http://www.opengis.net/def/samplingFeatureType/OGC-OM/2.0/SF_SamplingPoint\"/>"
                        "                <sf:sampledFeature xlink:href=\"http://www.opengis.net/def/nil/OGC/0/unknown\"/>"
                        "                <sams:shape>"
                        "                    <gml:Point gml:id=\"p_brisbane\">"
                        "                        <gml:pos srsName=\"http://www.opengis.net/def/crs/EPSG/0/4326\">51.935101100104916 7.651968812254194</gml:pos>"
                        "                    </gml:Point>"
                        "                </sams:shape>"
                        "            </sams:SF_SpatialSamplingFeature>"
                        "        </om:featureOfInterest>"
                        "        <om:result xsi:type=\"gml:MeasureType\" uom=\"degC\">17.5</om:result>"
                        "    </om:OM_Observation>"
                        "</sos:observation>"
                        "</sos:InsertObservation>";

HTTPClient sosIOhttp; // Http Client to send the request and get response back

/**
* The sosInsertObservation method connects to a WiFi network and 
* sends an XML data request to an SOS (Sensor Observation Service) server 
* to insert an observation. It constructs an HTTP POST request with XML data 
* detailing the observation. The method sends the request, retrieves the server's 
* response, prints the HTTP response code and payload to the serial monitor, and 
* updates timestamp values to simulate continuous submissions to record response latency
* for our experiment.
*/
void sosInsertObservation() {

  WiFi.begin(ssid, password); // begin Wi-Fi with ssid and password
  Serial.print("Connecting to WiFi");
  /*while (WiFi.status() != WL_CONNECTED) {
      delay(1500);
      Serial.print(".");
  }*/

  if(WiFi.status() == WL_CONNECTED) { // check if connected to Wi-Fi
  
    sosIOhttp.begin(sosIOurl);
    sosIOhttp.addHeader("Content-Type", "application/xml"); // Set Content-Type header
  
    for(int i = 0; i <1; i++) {
      // Send HTTP POST request

      sosIOxmlData = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                        "<sos:InsertObservation xmlns:sos=\"http://www.opengis.net/sos/2.0\" xmlns:swes=\"http://www.opengis.net/swes/2.0\" xmlns:swe=\"http://www.opengis.net/swe/2.0\" xmlns:sml=\"http://www.opengis.net/sensorML/1.0.1\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:sams=\"http://www.opengis.net/samplingSpatial/2.0\" xmlns:sf=\"http://www.opengis.net/sampling/2.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" service=\"SOS\" version=\"2.0.0\" xsi:schemaLocation=\"http://www.opengis.net/sos/2.0 http://schemas.opengis.net/sos/2.0/sos.xsd  http://www.opengis.net/samplingSpatial/2.0 http://schemas.opengis.net/samplingSpatial/2.0/spatialSamplingFeature.xsd\">"
                        "<sos:offering>Thermometer_1285_offering</sos:offering>"
                        "<sos:observation>"
                        "    <om:OM_Observation gml:id=\"o1\">"
                        "        <om:type xlink:href=\"http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement\"/>"
                        "        <om:phenomenonTime>"
                        "            <gml:TimeInstant gml:id=\"phenomenonTime\">"
                        "                <gml:timePosition>2023-" + String(sosIOmonthValue) + "-" + String(sosIOdayValue) +"T" + String(sosIOhourValue) + ":00:12.000+02:00</gml:timePosition>"
                        "            </gml:TimeInstant>"
                        "        </om:phenomenonTime>"
                        "        <om:resultTime xlink:href=\"#phenomenonTime\"/>"
                        "        <om:procedure xlink:href=\"Thermometer_1285\"/>"
                        "        <om:observedProperty xlink:href=\"air_temperature\"/>"
                        "        <om:featureOfInterest>"
                        "            <sams:SF_SpatialSamplingFeature gml:id=\"ssf_brisbane\">"
                        "                <gml:identifier codeSpace=\"\">Brisbane</gml:identifier>"
                        "                <gml:name>Brisbane</gml:name>"
                        "                <sf:type xlink:href=\"http://www.opengis.net/def/samplingFeatureType/OGC-OM/2.0/SF_SamplingPoint\"/>"
                        "                <sf:sampledFeature xlink:href=\"http://www.opengis.net/def/nil/OGC/0/unknown\"/>"
                        "                <sams:shape>"
                        "                    <gml:Point gml:id=\"p_brisbane\">"
                        "                        <gml:pos srsName=\"http://www.opengis.net/def/crs/EPSG/0/4326\">51.935101100104916 7.651968812254194</gml:pos>"
                        "                    </gml:Point>"
                        "                </sams:shape>"
                        "            </sams:SF_SpatialSamplingFeature>"
                        "        </om:featureOfInterest>"
                        "        <om:result xsi:type=\"gml:MeasureType\" uom=\"degC\">" + ReadSensorData() + "</om:result>"
                        "    </om:OM_Observation>"
                        "</sos:observation>"
                        "</sos:InsertObservation>";


      sosIOhttpResponseCode = sosIOhttp.POST(sosIOxmlData); // http post
      if (sosIOhttpResponseCode > 0) { // success response
        Serial.print("HTTP ");
        Serial.println(sosIOhttpResponseCode);
        sosIOpayload = sosIOhttp.getString();
        Serial.println(sosIOpayload);
      }
      else { // error response
        Serial.print("Error code: ");
        Serial.println(sosIOhttpResponseCode);
        Serial.println(":-(");
      }

      sosIOhourValue++; // hour value for multiple value to record response latency
      if(sosIOhourValue == 23) {
        sosIOdayValue++;
        sosIOhourValue = 1;
      }
      if(sosIOdayValue == 28) {
        sosIOmonthValue++;
        sosIOdayValue = 1;
        sosIOhourValue = 1;
      }
    }
  }
}


/**
* The ReadSensorData function configures the analog-to-digital converter (ADC) 
* resolution and pin mode for sensor input. It then computes and returns the 
* temperature value based on the analog input from the sensor, utilizing a 
* predefined mathematical formula for temperature calculation.
*/
float ReadSensorData() {
  analogReadResolution(10);
  pinMode(15, INPUT);
  return 1 / (log(1 / (1023. / analogRead(15) - 1)) / 3950 + 1.0 / 298.15) - 273.15;
}