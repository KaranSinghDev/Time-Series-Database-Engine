# GTest integration requires a slightly newer CMake version for FetchContent.
cmake_minimum_required(VERSION 3.13)
project(insight_engine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Fetch and Configure Google Test (GTest) ---
# This block tells CMake to automatically download and prepare GTest for our project,
# making our build self-contained and professional.
include(FetchContent)
FetchContent_Declare(
  googletest
  # Using a specific, version-locked tag is a best practice for reproducibility.
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
# The 'QUIET' flag prevents GTest's own build messages from cluttering our output.
FetchContent_MakeAvailable(googletest)


# --- Define Our Project's Targets ---

# 1. The main shared library (our database engine)
add_library(insight SHARED insight.cpp shard.cpp)
target_include_directories(insight PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# 2. The test executable
add_executable(engine_test test_engine.cpp insight.cpp shard.cpp)
target_include_directories(engine_test PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# --- Link GTest to Our Test Executable ---
# This is the crucial step that connects our test code to the GTest framework.
# GTest::gtest_main provides the necessary main() function and all assertion libraries.
target_link_libraries(engine_test PRIVATE GTest::gtest_main)


    
                                                               