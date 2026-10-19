cmake_minimum_required(VERSION 3.16)
project(bliss_mood_essentia_cpp_worker LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Link the original Essentia C++ library, NOT essentia-rs.
# Build/install Essentia separately against an audited native dependency set.
find_package(PkgConfig REQUIRED)
pkg_check_modules(ESSENTIA REQUIRED IMPORTED_TARGET essentia)
add_executable(bliss-essentia-worker essentia_cpp_worker.cpp)
target_link_libraries(bliss-essentia-worker PRIVATE PkgConfig::ESSENTIA)
if(MSVC)
    target_compile_options(bliss-essentia-worker PRIVATE /W4)
else()
    target_compile_options(bliss-essentia-worker PRIVATE -Wall -Wextra)
endif()

# Test protocol without installing Essentia: compile separately with c++.
add_executable(essentia-protocol-fixture protocol_fixture.cpp)
