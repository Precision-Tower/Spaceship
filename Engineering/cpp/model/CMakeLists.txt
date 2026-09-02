cmake_minimum_required(VERSION 3.20)

project(
    ceos_engineering_model
    VERSION 0.2.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(
    QPS_CORE_SOURCE_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/../qps/core/src"
)

file(GLOB_RECURSE QPS_LEXER_SOURCES
    "${QPS_CORE_SOURCE_DIR}/tokens/c/*.cpp"
)

file(GLOB_RECURSE QPS_AST_SOURCES
    "${QPS_CORE_SOURCE_DIR}/ast/*.cpp"
    "${QPS_CORE_SOURCE_DIR}/ast/c/*.cpp"
)

file(GLOB_RECURSE QPS_PARSER_SOURCES
    "${QPS_CORE_SOURCE_DIR}/parser/c/*.cpp"
    "${QPS_CORE_SOURCE_DIR}/parser/c/statements/*.cpp"
)

file(GLOB_RECURSE QPS_VISITOR_SOURCES
    "${QPS_CORE_SOURCE_DIR}/visitors/*.cpp"
    "${QPS_CORE_SOURCE_DIR}/visitors/c/*.cpp"
)

file(GLOB_RECURSE QPS_RUNTIME_SOURCES
    "${QPS_CORE_SOURCE_DIR}/runtime/c/*.cpp"
)

add_library(
    ceos_qps_runtime
    ${QPS_LEXER_SOURCES}
    ${QPS_AST_SOURCES}
    ${QPS_PARSER_SOURCES}
    ${QPS_VISITOR_SOURCES}
    ${QPS_RUNTIME_SOURCES}
    "${QPS_CORE_SOURCE_DIR}/utils.cpp"
)

target_include_directories(
    ceos_qps_runtime
    PUBLIC
        "${QPS_CORE_SOURCE_DIR}"
        "${QPS_CORE_SOURCE_DIR}/tokens/h"
        "${QPS_CORE_SOURCE_DIR}/ast"
        "${QPS_CORE_SOURCE_DIR}/ast/h"
        "${QPS_CORE_SOURCE_DIR}/parser/h"
        "${QPS_CORE_SOURCE_DIR}/parser/h/statements"
        "${QPS_CORE_SOURCE_DIR}/visitors"
        "${QPS_CORE_SOURCE_DIR}/visitors/h"
        "${QPS_CORE_SOURCE_DIR}/runtime/h"
)

target_compile_features(
    ceos_qps_runtime
    PUBLIC cxx_std_20
)

add_library(
    ceos_engineering_model
    src/quantity.cpp
    src/port.cpp
    src/design_instance.cpp
)

# QPS is an integration boundary, not part of the authoritative
# Engineering model implementation.
add_library(
    ceos_engineering_qps_adapter
    src/qps_design_adapter.cpp
    src/qps_quantity_adapter.cpp
)

target_include_directories(
    ceos_engineering_model
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(
    ceos_engineering_qps_adapter
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(
    ceos_engineering_qps_adapter
    PUBLIC
        ceos_engineering_model
        ceos_qps_runtime
)

target_compile_options(
    ceos_engineering_qps_adapter
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

target_compile_options(
    ceos_engineering_model
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

enable_testing()

add_executable(
    engineering_quantity_test
    tests/quantity_test.cpp
)
target_link_libraries(
    engineering_quantity_test
    PRIVATE ceos_engineering_model
)
add_test(
    NAME engineering_quantity_test
    COMMAND engineering_quantity_test
)

add_executable(
    engineering_port_test
    tests/port_test.cpp
)
target_link_libraries(
    engineering_port_test
    PRIVATE ceos_engineering_model
)
add_test(
    NAME engineering_port_test
    COMMAND engineering_port_test
)

add_executable(
    engineering_design_instance_test
    tests/design_instance_test.cpp
)
target_link_libraries(
    engineering_design_instance_test
    PRIVATE ceos_engineering_model
)
add_test(
    NAME engineering_design_instance_test
    COMMAND engineering_design_instance_test
)

add_executable(
    engineering_qps_design_adapter_test
    tests/qps_design_adapter_test.cpp
)
target_link_libraries(
    engineering_qps_design_adapter_test
    PRIVATE ceos_engineering_qps_adapter
)
add_test(
    NAME engineering_qps_design_adapter_test
    COMMAND engineering_qps_design_adapter_test
)
