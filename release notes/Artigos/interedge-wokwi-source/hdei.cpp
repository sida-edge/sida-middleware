/**
 * Module       : hdei : InterEdge 
 * Name         : hdei.cpp
 * Description  : This is the implementation file (.cpp) of our proposed
 * solution that contains the actual code for the functions and classes declared 
 * in our header file. It includes the definitions and implementations of the 
 * functions declared in the header file, along with any additional internal functions 
 * or variables required for the library's functionality. The implementation file is 
 * compiled along with the header file to produce the compiled library that can be 
 * linked with other programs. 
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

#include "Arduino.h"
#include "hdei.h"
#include "math.h"
#include "string.h"

/**
* Constructor Function that is called when 
* an object of this class is instantiated.
*/
HDEI::HDEI()
{

}

/**
* The method formula computes the result of a postfix expression 
* provided as input along with supplementary data. It initializes a tokenization 
* process to parse the expression and evaluate it using a stack-based algorithm. 
* Operand values and the specified data are pushed onto the stack, 
* while arithmetic and mathematical operations are performed based on the 
* operators encountered. Finally, the result of the expression evaluation is returned.
*/
float HDEI::formula(const char* expression, float data) {
  // Declare a pointer for tokenizing the expression
  char *tokens;
  // Create a copy of the input expression to avoid modifying the original
  char exprCopy[strlen(expression) + 1];
  // Copy the input expression to the newly created array
  strcpy(exprCopy, expression);

  // Initialize tokenization by splitting the expression based on spaces
  tokens = strtok(exprCopy, " ");
  // Declare a stack to store operands, with a maximum size of 20
  float stack[20]; 
  // Initialize the stack pointer to -1, indicating an empty stack
  int top = -1;

  // Loop through all tokens in the expression
  while (tokens != NULL) {
    // Check if the token is a number or a negative number
    if (isdigit(tokens[0]) || (tokens[0] == '-' && isdigit(tokens[1]))) {
      // Convert the token to a float and push it onto the stack
      stack[++top] = atof(tokens);
      // Check if the token is the variable 'V'
    } else if (strcmp(tokens, "V") == 0) {
      // Push the provided data value onto the stack
      stack[++top] = data;
    } else {
      // Pop the top two values from the stack for the operation
      float val2 = stack[top--];
      float val1 = stack[top--];
      // Perform the appropriate operation based on the token and push the result onto the stack
      if (strcmp(tokens, "+") == 0) {
        stack[++top] = val1 + val2;
      } else if (strcmp(tokens, "-") == 0) {
        stack[++top] = val1 - val2;
      } else if (strcmp(tokens, "*") == 0) {
        stack[++top] = val1 * val2;
      } else if (strcmp(tokens, "/") == 0) {
        stack[++top] = val1 / val2;
      } else if (strcmp(tokens, "log") == 0) {
        stack[++top] = log(val2);
      }
    }
    // Move to the next token in the expression
    tokens = strtok(NULL, " ");
  }

  // Return the final result from the top of the stack
  return stack[top];
}

/**
* The DataReadingSchedule method operates within the framework to 
* ascertain the current device from which data will be read, 
* given the input of the controller ID. It employs a predetermined 
* schedule or algorithm to map the controller ID to the corresponding device ID. 
* Upon receiving the controller ID, the method analyzes the schedule and 
* determines the device ID from which data should be currently retrieved. 
* Subsequently, it returns the identified device ID as the output, indicating the 
* device that is currently designated for data reading.
*/
String HDEI::DataReadingSchedule(String C)
{ 
  if(C == _CtrlRegisterESP32_ControllerId_pubID) {
    return _DevRegister1_DeviceId;
  } 
  else if(C == _CtrlRegisterUno_ControllerId_pubID) {
    return _DevRegister2_DeviceId;
  } 
  else {
    return _DevRegister1_DeviceId;
  }
}

/**
* The ReadData method retrieves and processes data from a specified source device. 
* It obtains the device's ID. The method then establishes a connection with the device. 
* It then reads the actual data from the device. The raw data is subsequently converted 
* using a predefined formula to ensure it meets the required format or units. 
* Finally, the method returns the converted data value. 
* This process ensures accurate and context-aware data retrieval from the device.
*/
float HDEI::ReadData(String device)
{ 
  float data;
  float resultData;

  if(device == "NTC6001") {
    analogReadResolution(10);
    pinMode(_DevRegister1_PIN, INPUT);
    data = analogRead(_DevRegister1_PIN);
    resultData = formula(_DevProfile_Formula.c_str(), data);
  } else {
    pinMode(_DevRegister2_PIN, INPUT);
    data = analogRead(_DevRegister2_PIN);
    resultData = formula(_DevProfile_Formula.c_str(), data);
  }

  return resultData;
}

/**
* The WriteData method is designed to send a specified action to a destination device. 
* Given the parameters of the destination device and the action, the method follows a 
* sequence of steps to accomplish this task. It first retrieves the device ID, 
* establishes a connection with the device. The action is then converted using a predefined 
* formula (if required) to obtain the final value. The method sends the combined command and 
* value to the destination device and returns a status indicating whether the data 
* was sent successfully. This ensures reliable and accurate data transmission 
* to the designated device. In this implementation, the absence of any actuators 
* obviates the necessity for sending commands or tasks to any devices or actuators. 
* Consequently, the WriteData method is not required and has not been implemented 
* for this particular scenario.
*/
void HDEI::WriteData(String Dd, String A)
{ 

}


/**
* The MessageReadingSchedule method operates within the framework to determine the 
* current controller from which a message should be read. It identifys the corresponding 
* controller register. Upon invocation, the method analyzes the schedule to 
* ascertain which controller is currently designated for message reading. 
* It then returns the identified controller register, indicating the controller 
* from which a message should now be read. This ensures systematic and timely message 
* retrieval from the appropriate controller. In this implementation, the absence 
* of multiple controllers obviates the necessity for reading any message from other controllers.
* Consequently, the MessageReadingSchedule method is not required and has not been implemented 
* for this particular scenario.
*/
String HDEI::MessageReadingSchedule(String C)
{ 
  
}

/**
* The NeedAction method is designed to determine if an action needs 
* to be taken based on a given value and predefined conditions. 
* It retrieves the device ID, then checks the value against the conditions 
* specified. If any condition necessitates an action, the method returns the action. 
* This ensures that the system can dynamically respond to specific conditions by 
* triggering appropriate actions. In this implementation, the absence of any actuators 
* obviates the necessity for sending commands or tasks to any devices or actuators. 
* Consequently, the NeedAction method is not required and has not been implemented 
* for this particular scenario.
*/
String HDEI::NeedAction(String C, String Ds, float V)
{ 
  
}

/**
* The ReadMessage method facilitates reading incoming messages for a 
* given controller. It checks for any incoming messages in the MessageBuffer, 
* and, if data is available, reads the incoming message. The method then returns 
* the message that was read. This process ensures that the controller can efficiently 
* retrieve and process messages as they arrive. In this implementation, the absence 
* of multiple controllers obviates the necessity for routing any message to other controllers,
* thus reading any message from a controller. Consequently, the ReadMessage method 
* is not required and has not been implemented for this particular scenario.
*/
String HDEI::ReadMessage(String C)
{ 
  
}

/**
* The WriteMessage method constructs a message for a destination device by 
* combining the specified action and the device's path within the network. 
* It retrieves the device ID and the corresponding destination device path. 
* The method then creates a message by combining the action with the destination 
* device path and returns the constructed message. In this implementation, the absence 
* of multiple controllers obviates the necessity for routing any message to other controllers,
* thus writing any message to any connected controller. 
* Consequently, the WriteMessage method is not required and has not been implemented 
* for this particular scenario.
*/
String HDEI::WriteMessage(String C, String Ds, String A)
{ 
  
}

/**
* The NeedRouting method determines whether routing is necessary for a 
* given source device by evaluating its connection within the network. It retrieves 
* the device ID, then obtains the corresponding destination device path. The method 
* returns true if the destination device is connected to another controller, indicating 
* that routing is needed. Otherwise, it returns false. In this implementation, the absence 
* of multiple controllers obviates the necessity for routing any message to other controllers. 
* Consequently, the NeedRouting method is not required and has not been implemented 
* for this particular scenario.
*/
bool HDEI::NeedRouting(String C, String Ds)
{

}

/**
* The RouteMessage method is designed to route messages 
* to the appropriate controller. It gets a message M, extracts the 
* next controller ID, and checks if this ID matches the current controller's ID. 
* If there is no match, the method routes the message to the next controller. 
* This ensures that messages are directed to the correct controller within the network.
* In this implementation, the absence of multiple controllers obviates the 
* necessity for routing any message to other controllers. Consequently, 
* the RouteMessage method is not required and has not been implemented 
* for this particular scenario.
*/
void HDEI::RouteMessage(String M)
{

}