cmake_minimum_required(VERSION 3.14)

project(SidaIngestion VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        add_compile_options(-O3)
    endif()
endif()

find_package(Threads REQUIRED)
find_package(cppzmq REQUIRED)
find_package(CURL REQUIRED)

add_subdirectory(core)
add_subdirectory(drivers/modbus)
# add_subdirectory(drivers/opcua)

# ---------------------------------------------------------
# Executável Principal
# ---------------------------------------------------------
# O arquivo main.cpp será criado na raiz em breve
add_executable(ingestion_service main.cpp)
target_link_libraries(ingestion_service 
    PRIVATE 
    sida_core 
    sida_modbus 
    cppzmq
    CURL::libcurl
)