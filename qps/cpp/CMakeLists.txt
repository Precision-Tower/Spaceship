# qps/CMakeLists.txt
cmake_minimum_required(VERSION 3.10)
project(QPS CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

# Define source directories
set(QPS_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Define all source files for the QPS executable
file(GLOB_RECURSE LEXER_SOURCES
    "${QPS_SOURCE_DIR}/tokens/c/*.cpp" # All .cpp files in tokens/c
)
file(GLOB_RECURSE AST_SOURCES
    "${QPS_SOURCE_DIR}/ast/*.cpp"       # For ast_utils.cpp
    "${QPS_SOURCE_DIR}/ast/c/*.cpp"     # For ast/c/*.cpp implementations
)
file(GLOB_RECURSE PARSER_SOURCES
    "${QPS_SOURCE_DIR}/parser/c/*.cpp"
    "${QPS_SOURCE_DIR}/parser/c/statements/*.cpp"
)
file(GLOB_RECURSE VISITOR_SOURCES
    "${QPS_SOURCE_DIR}/visitors/*.cpp"  # For ast_interface.hpp (if it were a .cpp file or similar)
    "${QPS_SOURCE_DIR}/visitors/c/*.cpp" # For visitors/c/*.cpp implementations
)

file(GLOB_RECURSE RUNTIME_SOURCES
    "${QPS_SOURCE_DIR}/runtime/c/*.cpp"
)

# Compile the QPS implementation once and link all executables against it.
set(QPS_CORE_SOURCES
    ${LEXER_SOURCES}
    ${AST_SOURCES}
    ${PARSER_SOURCES}
    ${VISITOR_SOURCES}
    ${RUNTIME_SOURCES}
    "${QPS_SOURCE_DIR}/utils.cpp"
)

add_library(qps_core STATIC ${QPS_CORE_SOURCES})

target_include_directories(
    qps_core
    PUBLIC
        "${QPS_SOURCE_DIR}"
        "${QPS_SOURCE_DIR}/tokens/h"
        "${QPS_SOURCE_DIR}/ast"
        "${QPS_SOURCE_DIR}/ast/h"
        "${QPS_SOURCE_DIR}/parser/h"
        "${QPS_SOURCE_DIR}/parser/h/statements"
        "${QPS_SOURCE_DIR}/visitors"
        "${QPS_SOURCE_DIR}/visitors/h"
        "${QPS_SOURCE_DIR}/runtime/h"
)

target_compile_features(qps_core PUBLIC cxx_std_17)

if(MSVC)
    target_compile_options(qps_core PRIVATE /W4)
else()
    target_compile_options(qps_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(qps "${QPS_SOURCE_DIR}/main.cpp")
target_link_libraries(qps PRIVATE qps_core)

function(add_qps_test target source)
    add_executable(${target} ${source})
    target_link_libraries(${target} PRIVATE qps_core)
    target_compile_features(${target} PRIVATE cxx_std_17)
endfunction()

add_qps_test(
    qps_symbol_resolver_test
    tests/runtime/symbol_resolver_test.cpp
)

add_qps_test(
    qps_reference_document_plan_test
    tests/runtime/reference_document_plan_test.cpp
)

add_qps_test(
    qps_structural_selection_test
    tests/runtime/structural_selection_test.cpp
)

add_qps_test(
    qps_path_resolver_test
    tests/runtime/path_resolver_test.cpp
)

add_qps_test(
    qps_execution_test
    tests/runtime/execution_test.cpp
)

add_qps_test(
    qps_runtime_semantics_test
    tests/runtime/execution_semantics_test.cpp
)

add_qps_test(
    qps_runtime_dictionary_test
    tests/runtime/runtime_dictionary_test.cpp
)

add_qps_test(
    qps_execution_definition_test
    tests/runtime/execution_definition_test.cpp
)

add_qps_test(
    qps_function_semantics_test
    tests/runtime/function_semantics_test.cpp
)

add_qps_test(
    qps_grammar_regression_test
    tests/parser/grammar_regression_test.cpp
)

add_qps_test(
    qps_geometry_execution_test
    tests/runtime/geometry_execution_test.cpp
)

add_qps_test(
    qps_host_action_test
    tests/runtime/host_action_test.cpp
)


add_test(
    NAME qps_structural_selection_test
    COMMAND qps_structural_selection_test
)

add_test(
    NAME qps_runtime_semantics_test
    COMMAND qps_runtime_semantics_test
)

add_test(
    NAME qps_runtime_dictionary_test
    COMMAND qps_runtime_dictionary_test
)


add_test(
    NAME qps_function_semantics_test
    COMMAND qps_function_semantics_test
)

add_test(
    NAME qps_execution_definition_test
    COMMAND qps_execution_definition_test
)

add_test(
    NAME qps_geometry_execution_test
    COMMAND qps_geometry_execution_test
)

add_test(
    NAME qps_host_action_test
    COMMAND qps_host_action_test
)


add_test(
    NAME qps_grammar_regression_test
    COMMAND qps_grammar_regression_test
)


add_test(
    NAME qps_parser_golden_01_key_term_item
    COMMAND qps "${CMAKE_CURRENT_SOURCE_DIR}/tests/golden/01_key_term_item.qps"
)

add_test(
    NAME qps_parser_golden_02_nested_component
    COMMAND qps "${CMAKE_CURRENT_SOURCE_DIR}/tests/golden/02_nested_component.qps"
)

add_test(
    NAME qps_parser_golden_03_nested_semantics
    COMMAND qps "${CMAKE_CURRENT_SOURCE_DIR}/tests/golden/03_nested_semantics.qps"
)

add_test(
    NAME qps_parser_golden_QPS_quicksheet
    COMMAND qps
        ${CMAKE_CURRENT_SOURCE_DIR}/../qps/docs/QPS.qps
)


add_test(
    NAME qps_reference_document_plan_test
    COMMAND qps_reference_document_plan_test
)

add_test(
    NAME qps_symbol_resolver_defs_p
    COMMAND qps_symbol_resolver_test
        "${CMAKE_CURRENT_SOURCE_DIR}/../../Engineering/qps"
)


add_test(
    NAME qps_path_resolver_index_surface
    COMMAND qps_path_resolver_test
)

# To build (from your build directory, after saving this change):
# 1. Re-configure CMake: cmake ..
# 2. Build: cmake --build . --config Release
# 3. Run: .\qps.exe <your_source_file.qps>


add_qps_test(
    qps_corpus_ast_conformance_test
    tests/runtime/corpus_ast_conformance_test.cpp
)

add_test(
    NAME qps_corpus_ast_conformance_test
    COMMAND
        qps_corpus_ast_conformance_test
        ${CMAKE_CURRENT_SOURCE_DIR}/../..
)


add_test(
    NAME qps_active_corpus_conformance
    COMMAND
        ${CMAKE_COMMAND} -E env
        QPS_EXECUTABLE=$<TARGET_FILE:qps>
        CEOS_ROOT=${CMAKE_CURRENT_SOURCE_DIR}/../..
        python3
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/corpus_conformance_test.py
)


add_test(
    NAME qps_test_suite_cli
    COMMAND
        ${CMAKE_COMMAND} -E env
        QPS_EXECUTABLE=$<TARGET_FILE:qps>
        CEOS_ROOT=${CMAKE_CURRENT_SOURCE_DIR}/../..
        python3
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/test_suite_cli_test.py
)

add_test(
    NAME qps_probe_cli
    COMMAND
        ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/probe_cli_test.py
        $<TARGET_FILE:qps>
)

add_test(
    NAME qps_dir_cli
    COMMAND
        ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/dir_cli_test.py
        $<TARGET_FILE:qps>
)

add_test(
    NAME qps_query_cli
    COMMAND
        python3
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/query_cli_test.py
        $<TARGET_FILE:qps>
)

add_test(
    NAME qps_cipher_cli
    COMMAND
        python3
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/cipher_cli_test.py
        $<TARGET_FILE:qps>
)

add_test(
    NAME qps_source_execution_cli
    COMMAND
        python3
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/runtime/source_execution_cli_test.py
        $<TARGET_FILE:qps>
)
