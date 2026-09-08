cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Custom partition table
set(EXTRA_PARTITION_TABLE_OFFSET 0x8000)
set(PARTITION_TABLE_CUSTOM "${CMAKE_SOURCE_DIR}/partitions_model.csv")
set(PARTITION_TABLE_FILENAME "partitions_model.csv")

project(battery_predictor)
