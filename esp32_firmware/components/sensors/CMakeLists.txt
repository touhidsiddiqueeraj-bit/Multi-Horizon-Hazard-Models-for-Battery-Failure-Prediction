idf_component_register(
    SRCS "sensors.c" "voltage_divider.c" "current_sensor.c" "temp_sensor.c" "rtc_sensor.c" "soh_calibrator.c"
    INCLUDE_DIRS "."
    REQUIRES driver
)
