# llama.cpp CUDA build prefix: must contain include/llama.h (or include/ggml/) and lib/
LLAMA_DIR ?= /usr/local
CXX ?= g++
CXXFLAGS ?= -std=c++17 -O3

jev-gpu: proxy.cpp
	$(CXX) $(CXXFLAGS) -o $@ proxy.cpp \
	  ../../src/wire.cpp ../../src/vocab.cpp ../../src/request_tokens.cpp \
	  -I ../../src -I ../../third_party \
	  -I $(LLAMA_DIR)/include -I $(LLAMA_DIR)/include/ggml \
	  -pthread -L $(LLAMA_DIR)/lib -lllama -lggml -Wl,-rpath,$(LLAMA_DIR)/lib

clean:
	rm -f jev-gpu

.PHONY: clean
