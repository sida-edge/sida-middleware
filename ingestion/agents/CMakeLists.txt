cmake_minimum_required(VERSION 3.29)

project(sida_agents VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/../../.cmake)
include(project)

add_subdirectory(/app/libs ${CMAKE_BINARY_DIR}/sida_libs)

add_subdirectory(dummy)