CC = gcc
PY ?= python3
CFLAGS = -O2 -Wall -Wextra -Wno-format-truncation -std=c11
LDLIBS = -lm

TREE_ENGINE = ../esp32_firmware/components/tree_engine/tree_engine.c
TREES_BIN   = ../esp32_firmware/main/trees.bin
NASA_CSV    = ../data/nasa_clean_filtered.csv
REF_CSV     = reference.csv
GEN_REF     = generate_reference.py

.PHONY: all clean run ref benchmark validate

all: test_engine $(REF_CSV)

$(REF_CSV): $(GEN_REF) $(NASA_CSV)
	$(PY) $(GEN_REF)

test_engine: test_engine.c $(TREE_ENGINE)
	$(CC) $(CFLAGS) -o $@ test_engine.c $(TREE_ENGINE) $(LDLIBS)

run: test_engine $(REF_CSV)
	./test_engine $(TREES_BIN) $(REF_CSV)

benchmark: test_engine $(REF_CSV)
	./test_engine $(TREES_BIN) $(REF_CSV) --benchmark

ref: $(REF_CSV)

validate:
	$(PY) full_validate.py

clean:
	rm -f test_engine $(REF_CSV) model_probas.csv
