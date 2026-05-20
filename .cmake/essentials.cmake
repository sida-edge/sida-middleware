##########################################################################################################################################
function(sida_cpp_library)
    cmake_parse_arguments(
        ARG 
        "STATIC;SHARED"                                       
        "NAME"
        "HDRS;SRCS;DEPS;MACROS;COMPILE_OPTIONS;INCLUDE_DIRS"
        ${ARGN}
    )

    if (NOT ARG_NAME)
        message(FATAL_ERROR "[SIDA CMake] sida_cpp_library: O argumento NAME é obrigatório.")
    endif()
    if (NOT ARG_SRCS)
        message(FATAL_ERROR "[SIDA CMake] sida_cpp_library (${ARG_NAME}): Nenhum arquivo fonte (SRCS) fornecido.")
    endif()

    set(LIB_TYPE STATIC)
    if (ARG_SHARED)
        set(LIB_TYPE SHARED)
    endif()

    add_library(${ARG_NAME} ${LIB_TYPE} ${ARG_SRCS} ${ARG_HDRS})

    target_include_directories(${ARG_NAME} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    )

    if (ARG_INCLUDE_DIRS)
        target_include_directories(${ARG_NAME} PUBLIC ${ARG_INCLUDE_DIRS})
    endif()

    if (ARG_DEPS)
        target_link_libraries(${ARG_NAME} PUBLIC ${ARG_DEPS})
    endif()

    if (ARG_MACROS)
        target_compile_definitions(${ARG_NAME} PUBLIC ${ARG_MACROS})
    endif()

    if (ARG_COMPILE_OPTIONS)
        target_compile_options(${ARG_NAME} PRIVATE ${ARG_COMPILE_OPTIONS})
    endif()

    add_library(sida::${ARG_NAME} ALIAS ${ARG_NAME})

endfunction()
        
