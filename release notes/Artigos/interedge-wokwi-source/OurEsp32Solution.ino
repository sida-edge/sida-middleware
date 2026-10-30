/**
 * Module       : hdei : InterEdge 
 * Name         : OurEsp32Solution.ino
 * Description  : This is the main file where we have the setup function.
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
#include "hdei.h"

HDEI  ourEsp32Solution; // Initialize for our solution

/**
 * This procedure invokes the functions within our 
 * framework to retrieve temperature readings from the designated 
 * temperature sensor. Initially, it triggers the data retrieval schedule 
 * to determine the current device for data acquisition. Subsequently, 
 * it acquires data from the identified device. 
 */
void Esp32ControllerProgram()
{
  //for loop to record response latency
  for(int i = 0; i < 1; i++) {
    //get the device to read data from
  	String Ds = ourEsp32Solution.DataReadingSchedule(ourEsp32Solution._CtrlRegisterESP32_ControllerId_pubID);
    //read data 
    float V = ourEsp32Solution.ReadData(Ds);
    Serial.print("Temperature: ");
    Serial.print(V);
    Serial.println(" ℃");
  }
  
}