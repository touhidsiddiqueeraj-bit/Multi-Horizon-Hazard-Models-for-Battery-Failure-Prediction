#!/usr/bin/env python3
"""Convert trees.bin to a PROGMEM header for Arduino."""
import os, sys

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "esp32_firmware", "main", "trees.bin"
    )
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(__file__), "models_data.h"
    )

    with open(src, "rb") as f:
        data = f.read()

    lines = [
        "#pragma once",
        "#include <Arduino.h>",
        "",
        f"// Auto-generated from {os.path.basename(src)} ({len(data)} bytes)",
        "// Do not edit. Run: python bin2c.py",
        "",
        "const uint8_t trees_bin[] PROGMEM = {",
    ]

    # Write 16 bytes per line
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_bytes = ", ".join(f"0x{b:02X}" for b in chunk)
        lines.append(f"  {hex_bytes},")

    lines += [
        "};",
        f"",
        f"const unsigned int trees_bin_len = {len(data)};",
        "",
    ]

    out = "\n".join(lines) + "\n"
    with open(dst, "w") as f:
        f.write(out)

    print(f"Written: {dst} ({len(data)} bytes -> {os.path.getsize(dst)} bytes source)")
    print(f"  Array size: {len(data)} bytes in PROGMEM")

if __name__ == "__main__":
    main()
