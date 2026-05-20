# libs/CMakeLists.txt

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../.cmake")
include(SidaMacros)

find_package(cppzmq REQUIRED)

add_subdirectory(network)