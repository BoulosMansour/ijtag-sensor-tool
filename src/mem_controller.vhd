-- Memory Controller with Sensor Integration Point
-- Tests: single sensor instance injection, complex comments with special chars

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity mem_controller is
    generic (
        ADDR_WIDTH : integer := 32;
        DATA_WIDTH : integer := 64
    );
    port (
        -- System interface
        clk  : in std_logic;
        rst_n : in std_logic;

        -- Memory interface
        mem_addr     : out std_logic_vector((ADDR_WIDTH - 1) downto 0);
        mem_data_in  : in  std_logic_vector((DATA_WIDTH - 1) downto 0); -- Data from memory
        mem_data_out : out std_logic_vector((DATA_WIDTH - 1) downto 0);
        mem_we       : out std_logic;
        mem_re       : out std_logic;
        mem_busy     : in  std_logic := '0'
    );
end mem_controller;

architecture rtl of mem_controller is
    component complex_alu is
        generic (WIDTH : integer := 32);
        port (
            clk          : in  std_logic;
            rst          : in  std_logic;
            operand_a    : in  std_logic_vector(63 downto 0);
            operand_b    : in  std_logic_vector(31 downto 0);
            result       : out std_logic_vector(63 downto 0);
            result_valid : out std_logic;
            overflow     : out std_logic;
            underflow    : out std_logic;
            carry        : out std_logic
        );
    end component;

    -- SENSOR-DECLARATION: thermal_sensor

    signal alu_result   : std_logic_vector(63 downto 0);
    signal alu_valid    : std_logic;
    signal temp_sensor  : std_logic_vector(7 downto 0);
    signal sensor_alert : std_logic;
    signal mem_addr_int : std_logic_vector((ADDR_WIDTH - 1) downto 0) := (others => '0');

begin

    mem_addr <= mem_addr_int;

    -- ALU instance for address calculation
    alu_inst : complex_alu
        generic map (WIDTH => 32)
        port map (
            clk          => clk,
            rst          => rst_n,
            operand_a    => mem_data_in,
            operand_b    => mem_addr_int(31 downto 0),
            result       => alu_result,
            result_valid => alu_valid,
            overflow     => open,
            underflow    => open,
            carry        => open
        );

    -- SENSOR-INSTANTIATION: thermal_inst_1

end rtl;
