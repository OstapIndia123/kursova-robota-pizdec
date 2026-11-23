cmake_minimum_required(VERSION 3.16)
project(oop_coursework_2026 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(coursework_core
    src/cone.cpp
    src/cylinder.cpp
    src/file_processor.cpp
    src/result_writer.cpp
    src/shape_factory.cpp
    src/tetrahedron.cpp
)
target_include_directories(coursework_core PUBLIC include)
function(enable_project_warnings target)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /permissive-)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow)
    endif()
endfunction()
enable_project_warnings(coursework_core)

add_executable(shape_ratio src/main.cpp)
target_link_libraries(shape_ratio PRIVATE coursework_core)
enable_project_warnings(shape_ratio)

include(CTest)
if(BUILD_TESTING)
    add_executable(coursework_tests tests/test_main.cpp)
    target_link_libraries(coursework_tests PRIVATE coursework_core)
    enable_project_warnings(coursework_tests)
    add_test(NAME coursework_tests COMMAND coursework_tests)
endif()
