find_package(open62541 REQUIRED)

add_library(sida_opcua STATIC OpcUaDriver.cpp)

target_include_directories(sida_opcua PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(sida_opcua PUBLIC 
    sida_core 
    open62541::open62541
)