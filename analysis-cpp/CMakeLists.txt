cmake_minimum_required(VERSION 3.16)

project(codeseer_analysis_cpp LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)

message(STATUS "LLVM include dirs: ${LLVM_INCLUDE_DIRS}")
message(STATUS "Clang include dirs: ${CLANG_INCLUDE_DIRS}")

add_executable(codeseer_analyzer
    src/main.cpp
)

# 🔑 THIS IS THE CRITICAL PART
target_include_directories(codeseer_analyzer
    PRIVATE
    ${LLVM_INCLUDE_DIRS}
    ${CLANG_INCLUDE_DIRS}
)

# 🔑 Use imported Clang targets (correct way)
target_link_libraries(codeseer_analyzer
    PRIVATE
    clangTooling
    clangBasic
    clangAST
    clangFrontend
    clangSerialization
)

