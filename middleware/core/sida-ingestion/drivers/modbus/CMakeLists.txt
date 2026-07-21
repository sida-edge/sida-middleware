find_package(PkgConfig REQUIRED)
pkg_check_modules(MODBUS REQUIRED libmodbus)

add_library(sida_modbus STATIC ModbusDriver.cpp)

target_include_directories(sida_modbus PUBLIC 
    ${CMAKE_CURRENT_SOURCE_DIR} 
    ${MODBUS_INCLUDE_DIRS}
)

target_link_libraries(sida_modbus PUBLIC 
    sida_core 
    ${MODBUS_LIBRARIES}
)