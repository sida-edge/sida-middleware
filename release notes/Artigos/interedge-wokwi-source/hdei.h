/**
 * Module       : hdei : InterEdge 
 * Name         : hdei.h
 * Description  : This is the header (.h) file that contains declarations, 
 * including function prototypes, class definitions, constants, and other 
 * necessary declarations, to provide an interface for using the library's 
 * functionality. It serves as a contract or blueprint for how the library 
 * can be utilized by external programs. 
 * 
 * Due to limitations in uploading text files within the online simulator's 
 * controllers, instead of utilizing text files to store parameter values for 
 * device and controller profiles, as well as for device and controller registers, 
 * corresponding variables mirroring these parameters along with their values were 
 * generated. These variables, serving as substitutes for the parameters, were 
 * declared as private values in the header file to uphold security measures. 
 * 
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
#ifndef hdei_h
#define hdei_h

#include "Arduino.h"
#include "math.h"
#include "string.h"

class HDEI
{
  public:
    HDEI();
    float formula(const char* expression, float data);

    String DataReadingSchedule(String C);
    String MessageReadingSchedule(String C);
    
    float ReadData(String device);
    void WriteData(String Dd, String A);

    String ReadMessage(String C);
    String WriteMessage(String C, String Ds, String A);

    String NeedAction(String C, String Ds, float V);
    bool NeedRouting(String C, String Ds);
    void RouteMessage(String M);
    
    
    String _CtrlRegisterESP32_ControllerId_pubID = "ESP32001";
    String _CtrlRegisterUno_ControllerId_pubID = "Uno001";
    //String _DevProfile_Formula_infix = "1 / (log(1 / (1023.0 / V - 1)) / 3950 + 1.0 / 298.15) - 273.15"; 
  private:
    int _pin;
    bool _status;
    const float BETA = 3950;

    String _DevProfile_TypeID = "Type001";
    String _DevProfile_TypeName = "NTC";   
    String _DevProfile_Category = "Sensor";   
    String _DevProfile_SubCategory = "Temperature";
    String _DevProfile_TransmissionMode = "Read";  
    String _DevProfile_Connectivity = "Wired";
    String _DevProfile_DataType = "Float";
    int    _DevProfile_DataLength = 5;  
    String _DevProfile_MeasuringUnit = "celcius"; 
    String _DevProfile_NeedFormula = "Yes";  
    String _DevProfile_Formula = "1 1023.0 V / 1 - log 3950 / 1.0 298.15 / + / 273.15 -"; 
    String _DevProfile_ReadMethod = "ReadData";

    String _DataProfile_Id = "Format001"; 
    String _DataProfile_Name = "Digital Signal";  
    String _DataProfile_Version = "DS01";  
    String _DataProfile_DataType = "Digital Signal";
    String _DataProfile_Encoding = "N/A";   


    String _CtrlProfileESP32_TypeID = "ContType001";
    String _CtrlProfileESP32_TypeName = "ESP32"; 
    String _CtrlProfileESP32_Category = "Xtensa LX6 microarchitecture";  
    String _CtrlProfileESP32_Connectivity = "Wired"; 
    String _CtrlProfileESP32_NetworkProfile = "N/A";  
    String _CtrlProfileESP32_OrganizationProfile  = "N/A";

  

    String _DevRegister1_DeviceId = "NTC6001"; 
    String _DevRegister1_DeviceName = "Basic NTC Thermistor";
    int    _DevRegister1_PIN = 15;
    String _DevRegister1_TransmissionMode = "Read";
    String _DevRegister1_Connectivity = "Wired";
    String _DevRegister1_DeviceProfile = "Type001";
    String _DevRegister1_DataProfile = "Format001";
    String _DevRegister1_NetworkProfile = "N/A";
    String _DevRegister1_OrganizationProfile = "N/A";
    String _DevRegister1_ActualValue = "N/A";
    String _DevRegister1_ConvertedValue = "N/A";

    String _CtrlRegisterESP32_ControllerId = "ESP32001"; 
    String _CtrlRegisterESP32_ControllerName = "ESP32"; 
    String _CtrlRegisterESP32_ConnectedDevices ="NTC6001";
    String _CtrlRegisterESP32_ConnectedControllers = "N/A";
    String _CtrlRegisterESP32_Connectivity = "Wired";
    String _CtrlRegisterESP32_NetworkProfile = "N/A"; 
    String _CtrlRegisterESP32_OrganizationProfile = "N/A";
    String _CtrlRegisterESP32_SourceDevices = "ESP32001-NTC6001";
    String _CtrlRegisterESP32_ConditionActions = "N/A"; 
    String _CtrlRegisterESP32_DestinationDevices = "N/A";
    int    _CtrlRegisterESP32_DeviceProbeIntervals = 5;
    String _CtrlRegisterESP32_MessageBuffer = "NULL";
    String _CtrlRegisterESP32_ControllerProbeIntervals = "N/A";


    String _CtrlProfileUno_TypeID = "ContType002";
    String _CtrlProfileUno_TypeName = "Arduino Uno R3"; 
    String _CtrlProfileUno_Category = "AVR microarchitecture";  
    String _CtrlProfileUno_Connectivity = "Wired"; 
    String _CtrlProfileUno_NetworkProfile = "N/A";  
    String _CtrlProfileUno_OrganizationProfile  = "N/A"; 

    String _CtrlRegisterUno_ControllerId = "Uno001"; 
    String _CtrlRegisterUno_ControllerName = "Arduino Uno R3"; 
    String _CtrlRegisterUno_ConnectedDevices ="NTC6002";
    String _CtrlRegisterUno_ConnectedControllers = "N/A";
    String _CtrlRegisterUno_Connectivity = "Wired";
    String _CtrlRegisterUno_NetworkProfile = "N/A"; 
    String _CtrlRegisterUno_OrganizationProfile = "N/A";
    String _CtrlRegisterUno_SourceDevices = "Uno001-NTC6002";
    String _CtrlRegisterUno_ConditionActions = "N/A"; 
    String _CtrlRegisterUno_DestinationDevices = "N/A";
    int    _CtrlRegisterUno_DeviceProbeIntervals = 5;
    String _CtrlRegisterUno_MessageBuffer = "NULL";
    String _CtrlRegisterUno_ControllerProbeIntervals = "N/A";

    String _DevRegister2_DeviceId = "NTC6002"; 
    String _DevRegister2_DeviceName = "Basic NTC Thermistor";
    int    _DevRegister2_PIN = A0;
    String _DevRegister2_TransmissionMode = "Read";
    String _DevRegister2_Connectivity = "Wired";
    String _DevRegister2_DeviceProfile = "Type001";
    String _DevRegister2_DataProfile = "Format001";
    String _DevRegister2_NetworkProfile = "N/A";
    String _DevRegister2_OrganizationProfile = "N/A";
    String _DevRegister2_ActualValue = "N/A";
    String _DevRegister2_ConvertedValue = "N/A";

};


#endi