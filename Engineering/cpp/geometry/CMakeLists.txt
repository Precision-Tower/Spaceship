cmake_minimum_required(VERSION 3.20)

project(
    ceos_engineering_geometry
    VERSION 0.1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Native CAD kernel.
#
# OCCT is an implementation dependency of Engineering geometry.
# Its types do not cross the public Engineering geometry contract.
find_package(
    OpenCASCADE REQUIRED
    COMPONENTS
        FoundationClasses
        ModelingData
        ModelingAlgorithms
)

add_library(
    ceos_engineering_geometry
    src/feature/feature_dag.cpp
    src/build_plan/geometry_build_plan.cpp
    src/policy/modeling_policy.cpp
)

target_include_directories(
    ceos_engineering_geometry
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(
    ceos_engineering_geometry
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

enable_testing()

add_executable(
    engineering_geometry_contracts_test
    tests/geometry_contracts_test.cpp
)

target_link_libraries(
    engineering_geometry_contracts_test
    PRIVATE
        ceos_engineering_geometry
)

add_test(
    NAME engineering_geometry_contracts_test
    COMMAND engineering_geometry_contracts_test
)

# Engineering model is authoritative instance state.
# Geometry depends on the core model, never the QPS adapter.
add_subdirectory(
    ${CMAKE_CURRENT_SOURCE_DIR}/../model
    ${CMAKE_CURRENT_BINARY_DIR}/engineering-model
)

target_sources(
    ceos_engineering_geometry
    PRIVATE
        src/compiler/geometry_compiler.cpp
        src/navigation/geometry_navigation.cpp
        src/native/occt/geometry_executor.cpp
)

target_link_libraries(
    ceos_engineering_geometry
    PUBLIC
        ceos_engineering_model
    PRIVATE
        TKPrim
        TKTopAlgo
        TKBRep
        TKMesh
)

add_executable(
    engineering_geometry_compiler_test
    tests/geometry_compiler_test.cpp
)

target_link_libraries(
    engineering_geometry_compiler_test
    PRIVATE
        ceos_engineering_geometry
)

add_test(
    NAME engineering_geometry_compiler_test
    COMMAND engineering_geometry_compiler_test
)

add_executable(
    engineering_geometry_navigation_test
    tests/geometry_navigation_test.cpp
)

target_link_libraries(
    engineering_geometry_navigation_test
    PRIVATE
        ceos_engineering_geometry
)

add_test(
    NAME engineering_geometry_navigation_test
    COMMAND engineering_geometry_navigation_test
)

add_executable(
    engineering_native_geometry_executor_test
    tests/native_geometry_executor_test.cpp
)

target_link_libraries(
    engineering_native_geometry_executor_test
    PRIVATE
        ceos_engineering_geometry
)

add_test(
    NAME engineering_native_geometry_executor_test
    COMMAND engineering_native_geometry_executor_test
)

# QPS-to-Engineering geometry integration boundary.
#
# The core geometry library remains QPS-free.
# This adapter consumes already-resolved QPS geometry actions and
# translates them into kernel-neutral Engineering FeatureNodes.
add_library(
    ceos_engineering_qps_geometry_adapter
    src/adapters/qps/qps_geometry_adapter.cpp
)

target_include_directories(
    ceos_engineering_qps_geometry_adapter
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(
    ceos_engineering_qps_geometry_adapter
    PUBLIC
        ceos_engineering_geometry
        ceos_engineering_qps_adapter
        ceos_qps_runtime
)

target_compile_options(
    ceos_engineering_qps_geometry_adapter
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

add_executable(
    engineering_qps_geometry_adapter_test
    tests/qps_geometry_adapter_test.cpp
)

target_link_libraries(
    engineering_qps_geometry_adapter_test
    PRIVATE
        ceos_engineering_qps_geometry_adapter
)

add_test(
    NAME engineering_qps_geometry_adapter_test
    COMMAND engineering_qps_geometry_adapter_test
)

# End-to-end geometry artery:
# authored QPS -> Engineering structure -> native OCCT geometry.
add_executable(
    engineering_qps_native_geometry_test
    tests/qps_native_geometry_test.cpp
)

target_link_libraries(
    engineering_qps_native_geometry_test
    PRIVATE
        ceos_engineering_qps_geometry_adapter
        ceos_engineering_geometry
)

add_test(
    NAME engineering_qps_native_geometry_test
    COMMAND engineering_qps_native_geometry_test
)
