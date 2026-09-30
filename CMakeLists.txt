cmake_minimum_required(VERSION 3.24)
project(jev CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# OpenVINO runs the model. Its C++ SDK ships with the Python wheel (pip install -r requirements.txt):
#   -DOpenVINO_DIR=<site-packages>/openvino/cmake
find_package(OpenVINO REQUIRED COMPONENTS Runtime)

# llama.cpp, pinned: only its tokenizer, which gives the Python engine's token ids. Built from source and
# linked statically, without any compute backend (the vocabulary is read with vocab_only). Patched: its
# MiniCPM5 pre-tokenizer runs std::regex, which overflows the stack (libstdc++) or gives up (MSVC) on long
# words; third_party/llama-minicpm5 splits as that regex does, without recursion (tests/tokenizer.py checks).
include(FetchContent)
set(BUILD_SHARED_LIBS OFF)
foreach(off GGML_CPU GGML_OPENMP GGML_METAL GGML_BLAS GGML_ACCELERATE GGML_LLAMAFILE GGML_NATIVE LLAMA_BUILD_COMMON LLAMA_BUILD_TESTS
            LLAMA_BUILD_TOOLS LLAMA_BUILD_EXAMPLES LLAMA_BUILD_SERVER LLAMA_BUILD_APP LLAMA_BUILD_HTML LLAMA_OPENSSL)
  set(${off} OFF CACHE BOOL "" FORCE)
endforeach()
FetchContent_Declare(llama_cpp
  URL https://github.com/ggml-org/llama.cpp/archive/refs/tags/b11239.tar.gz
  URL_HASH SHA256=31589d37eb0010db094394b358f00cf6a7cc4bda27dc55a747d575a951e4afd4
  DOWNLOAD_EXTRACT_TIMESTAMP ON
  PATCH_COMMAND "${CMAKE_COMMAND}" -P "${CMAKE_CURRENT_SOURCE_DIR}/third_party/llama-minicpm5/apply.cmake")
FetchContent_MakeAvailable(llama_cpp)

add_executable(jev src/main.cpp src/server.cpp src/wire.cpp src/request_tokens.cpp src/vocab.cpp src/model.cpp)
target_include_directories(jev PRIVATE src third_party)
target_link_libraries(jev PRIVATE openvino::runtime llama)
# OpenVINO's libraries go beside the binary (scripts/build.py): found there, wherever it is unpacked.
if(APPLE)
  set_target_properties(jev PROPERTIES BUILD_RPATH "@loader_path" INSTALL_RPATH "@loader_path")
elseif(UNIX)
  set_target_properties(jev PROPERTIES BUILD_RPATH "$ORIGIN" INSTALL_RPATH "$ORIGIN")
endif()
if(MSVC)
  target_compile_options(jev PRIVATE /utf-8 /O2 /EHsc /W3 /bigobj)
  target_compile_definitions(jev PRIVATE NOMINMAX _WIN32_WINNT=0x0A00 _CRT_SECURE_NO_WARNINGS)
else()
  target_compile_options(jev PRIVATE -O2 -Wall -Wextra)
  target_link_libraries(jev PRIVATE pthread)
endif()

# The tokenizer's token ids for tests/tokenizer.py.
add_executable(tokenizer-test tests/tokenizer_test.cpp src/vocab.cpp)
target_include_directories(tokenizer-test PRIVATE src third_party)
target_link_libraries(tokenizer-test PRIVATE llama)
if(MSVC)
  target_compile_options(tokenizer-test PRIVATE /utf-8 /EHsc /W3)
endif()

# A choice's distribution from its options' yes/no answers (src/choice.hpp), checked without a model.
add_executable(choice-test tests/choice_test.cpp)
target_include_directories(choice-test PRIVATE src)
if(MSVC)
  target_compile_options(choice-test PRIVATE /utf-8 /EHsc /W3)
endif()

# How requests are split into model calls (src/calls.hpp), checked without a model.
add_executable(plan-calls-test tests/plan_calls_test.cpp)
target_include_directories(plan-calls-test PRIVATE src)
if(MSVC)
  target_compile_options(plan-calls-test PRIVATE /utf-8 /EHsc /W3)
endif()
