/**
 * Module       : hdei : InterEdge 
 * Name         : OurUnoSolution.ino
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

HDEI  ourUnoSolution; // initialize for our solution

/**
 * This procedure invokes the functions within our 
 * framework to retrieve temperature readings from the designated 
 * temperature sensor. Initially, it triggers the data retrieval schedule 
 * to determine the current device for data acquisition. Subsequently, 
 * it acquires data from the identified device. Transitioning to Arduino 
 * controller is necessary for data retrieval using the Arduino controller.
 */
void UnoControllerProgram()
{
  //for loop to record response latency
  for(int i = 0; i < 1; i++) {
    //get the device to read data from
  	String Ds = ourUnoSolution.DataReadingSchedule(ourUnoSolution._CtrlRegisterUno_ControllerId_pubID);
    //read data 
    float V = ourUnoSolution.ReadData(Ds);
    Serial.print("Uno Temperature: ");
    Serial.print(V);
    Serial.println(" ℃");
  }
  
}
