add_library(sida_core 
    STATIC 
    ManifestParser.cpp
    DriverWorker.cpp
)

target_include_directories(sida_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(sida_core PUBLIC Threads::Threads)