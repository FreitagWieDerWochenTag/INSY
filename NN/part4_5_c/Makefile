# Parts 4/5 (C forward inference) and a host build of the ESP32 sketch (Part 6).
# Run from the NN folder: make -C part4_5_c test

CC       ?= cc
CXX      ?= c++
CFLAGS   ?= -std=c99 -O2 -Wall -Wextra -Werror
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Werror
MODEL_DIR ?= ../models
BUILD    ?= build

LIB      = lib/nn
NN_SRC   = $(LIB)/nn.c
NN_DEPS  = $(LIB)/nn.h $(NN_SRC)
HEADER   = $(MODEL_DIR)/7seg_net.h
ESP32    = ../part6_esp32

.PHONY: all test web clean
all: $(BUILD)/test_txt $(BUILD)/test_header $(BUILD)/nn_cli_txt $(BUILD)/nn_cli_h $(BUILD)/esp32_sim

$(BUILD):
	mkdir -p $@

# Part 4: weights from the .txt file at run time
$(BUILD)/test_txt: test_txt.c seg_test.h $(NN_DEPS) | $(BUILD)
	$(CC) $(CFLAGS) -I$(LIB) test_txt.c $(NN_SRC) -lm -o $@

$(BUILD)/nn_cli_txt: nn_cli.c $(NN_DEPS) | $(BUILD)
	$(CC) $(CFLAGS) -I$(LIB) nn_cli.c $(NN_SRC) -lm -o $@

# Part 5: weights compiled in from the generated header (rebuilt when the header changes)
$(BUILD)/test_header: test_header.c seg_test.h $(LIB)/nn_from_header.h $(HEADER) $(NN_DEPS) | $(BUILD)
	$(CC) $(CFLAGS) -I$(LIB) -I$(MODEL_DIR) test_header.c $(NN_SRC) -lm -o $@

$(BUILD)/nn_cli_h: nn_cli.c $(LIB)/nn_from_header.h $(HEADER) $(NN_DEPS) | $(BUILD)
	$(CC) $(CFLAGS) -DNN_FROM_HEADER -I$(LIB) -I$(MODEL_DIR) nn_cli.c $(NN_SRC) -lm -o $@

# Part 6: the unchanged ESP32 sketch, linked against a host mock of the Arduino API
$(BUILD)/nn.o: $(NN_DEPS) | $(BUILD)
	$(CC) $(CFLAGS) -I$(LIB) -c $(NN_SRC) -o $@

$(BUILD)/esp32_sim: $(ESP32)/src/main.cpp $(ESP32)/sim/Arduino.h $(ESP32)/sim/sim_main.cpp \
		$(BUILD)/nn.o $(LIB)/nn_from_header.h $(HEADER) | $(BUILD)
	$(CXX) $(CXXFLAGS) -I$(ESP32)/sim -I$(LIB) -I$(MODEL_DIR) \
		$(ESP32)/src/main.cpp $(ESP32)/sim/sim_main.cpp $(BUILD)/nn.o -lm -o $@

test: $(BUILD)/test_txt $(BUILD)/test_header
	$(BUILD)/test_txt $(MODEL_DIR)/7seg.txt $(MODEL_DIR)/7seg_trained_predictions.json
	@echo
	$(BUILD)/test_header $(MODEL_DIR)/7seg_trained_predictions.json

# WebAssembly builds of the same sources for the web page (needs Emscripten: brew install emscripten)
EMCC     ?= emcc
EMXX     ?= em++
WEB_OUT  ?= ../web/build/wasm
EMFLAGS  = -O2 -sMODULARIZE -sENVIRONMENT=web,worker,node -sALLOW_MEMORY_GROWTH
CLI_FLAGS = $(EMFLAGS) -sINVOKE_RUN=0 -sEXIT_RUNTIME=0 -sEXPORTED_RUNTIME_METHODS=callMain,FS

web: $(WEB_OUT)/nn_txt.js $(WEB_OUT)/nn_h.js $(WEB_OUT)/esp32.js

$(WEB_OUT):
	mkdir -p $@

# Part 4: the page writes 7seg.txt into the virtual file system and calls main(MODEL.txt, BITS)
$(WEB_OUT)/nn_txt.js: nn_cli.c $(NN_DEPS) | $(WEB_OUT)
	$(EMCC) $(CFLAGS) -I$(LIB) nn_cli.c $(NN_SRC) $(CLI_FLAGS) -sEXPORT_NAME=createNnTxt -o $@

# Part 5: weights compiled in from the header, main(BITS)
$(WEB_OUT)/nn_h.js: nn_cli.c $(LIB)/nn_from_header.h $(HEADER) $(NN_DEPS) | $(WEB_OUT)
	$(EMCC) $(CFLAGS) -DNN_FROM_HEADER -I$(LIB) -I$(MODEL_DIR) nn_cli.c $(NN_SRC) $(CLI_FLAGS) -sEXPORT_NAME=createNnH -o $@

# Part 6: the unchanged sketch with the browser runner instead of sim_main.cpp
$(BUILD)/nn_wasm.o: $(NN_DEPS) | $(BUILD)
	$(EMCC) $(CFLAGS) -I$(LIB) -c $(NN_SRC) -o $@

$(WEB_OUT)/esp32.js: $(ESP32)/src/main.cpp $(ESP32)/sim/Arduino.h $(ESP32)/sim/web_main.cpp \
		$(BUILD)/nn_wasm.o $(LIB)/nn_from_header.h $(HEADER) | $(WEB_OUT)
	$(EMXX) $(CXXFLAGS) -I$(ESP32)/sim -I$(LIB) -I$(MODEL_DIR) $(ESP32)/src/main.cpp \
		$(ESP32)/sim/web_main.cpp $(BUILD)/nn_wasm.o $(EMFLAGS) -sEXPORT_NAME=createEsp32 \
		-sEXPORTED_FUNCTIONS=_sim_start,_sim_send,_sim_pin_mode,_sim_pin_level -sEXPORTED_RUNTIME_METHODS=ccall -o $@

clean:
	rm -rf $(BUILD) $(WEB_OUT)
