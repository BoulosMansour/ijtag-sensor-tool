-- Thermal Sensor ICL Blueprint
-- Defines the test interface for IEEE 1687 IJTAG integration

instr_def ThermalResetInstr() {
    bit [7:0] data;
};

instr_def ThermalReadTempInstr() {
    bit [7:0] temp_value;
    bit [2:0] status;
};

instr_def ThermalConfigInstr() {
    bit [7:0] threshold;
    bit enable_alert;
};

node ThermalSensor {
    trst_n = 1;
    instruction ThermalResetInstr;
    instruction ThermalReadTempInstr;
    instruction ThermalConfigInstr;
};
