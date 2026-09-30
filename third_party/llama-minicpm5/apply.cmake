# Adds a pre-tokenizer for MiniCPM5 to llama.cpp's src/unicode.cpp (run by FetchContent in the llama.cpp
# source folder): the splitters of splitters.cpp before Qwen2's, and their dispatch (dispatch.cpp) before
# the Han pattern's. Without it the MiniCPM5 patterns run on std::regex, which recurses once per character
# of a match: libstdc++ overflows the stack on a long word, MSVC gives up (error_complexity) on long runs of
# newlines. The splitters split as that regex does (tests/tokenizer.py checks the token ids).
set(file "src/unicode.cpp")
file(READ "${file}" text)
file(READ "${CMAKE_CURRENT_LIST_DIR}/splitters.cpp" splitters)
file(READ "${CMAKE_CURRENT_LIST_DIR}/dispatch.cpp" dispatch)
set(before_qwen2 "// Qwen2 system regex: \"(?i:")
set(before_han "    } else if (regex_expr == \"\\\\p{Han}+\") {")
foreach(anchor IN ITEMS "${before_qwen2}" "${before_han}")
  string(FIND "${text}" "${anchor}" first)
  string(FIND "${text}" "${anchor}" last REVERSE)
  if(first EQUAL -1 OR NOT first EQUAL last)
    message(FATAL_ERROR "llama.cpp ${file}: '${anchor}' is not there exactly once; the pinned llama.cpp changed")
  endif()
endforeach()
string(FIND "${text}" "unicode_regex_split_custom_minicpm5" done)
if(NOT done EQUAL -1)
  message(FATAL_ERROR "llama.cpp ${file} already has the MiniCPM5 splitters")
endif()
string(REPLACE "${before_qwen2}" "${splitters}${before_qwen2}" text "${text}")
string(REPLACE "${before_han}" "${dispatch}${before_han}" text "${text}")
file(WRITE "${file}" "${text}")
