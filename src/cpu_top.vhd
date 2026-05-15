-- Top-level CPU Entity with Sensor Injection Points
-- Tests: pragma handling, nested components, multi-instance injection

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity cpu_top is
    generic (
        DATA_WIDTH : integer := 32;
        ADDR_WIDTH : integer := 16
    );
    port (
        clk         : in  std_logic;
        rst_n       : in  std_logic;
        -- AXI-like interface
        axi_data_in : in  std_logic_vector((DATA_WIDTH - 1) downto 0);
        axi_valid   : in  std_logic;
        axi_ready   : out std_logic;
        -- Temperature monitoring
        temp_alert  : out std_logic;
        -- IJTAG interface
        ijtag_tck   : in  std_logic;
        ijtag_tms   : in  std_logic;
        ijtag_tdi   : in  std_logic;
        ijtag_tdo   : out std_logic
    );
end cpu_top;

architecture Behavioral of cpu_top is

    -- Component declarations
    component comp_a is
        generic (WIDTH : integer := 8);
        port (
            clk      : in  std_logic;
            data_in  : in  std_logic_vector(7 downto 0);
            data_out : out std_logic_vector(7 downto 0)
        );
    end component;

    component comp_b is
        port (
            data_in : in  std_logic_vector(7 downto 0);
            result  : out std_logic
        );
    end component;

    -- SENSOR-DECLARATION: thermal_sensor

    -- Internal signals
    signal comp_a_out   : std_logic_vector(7 downto 0);
    signal temp_value   : std_logic_vector(7 downto 0);
    signal sensor_status : std_logic_vector(2 downto 0);
    signal diag_bus     : std_logic_vector(7 downto 0);

begin

    -- Instantiate Component A
    i_comp_a : comp_a
        generic map (WIDTH => 8)
        port map (
            clk      => clk,
            data_in  => axi_data_in(7 downto 0),
            data_out => comp_a_out
        );

    -- Instantiate Component B
    i_comp_b : comp_b
        port map (
            data_in => comp_a_out,
            result  => axi_ready
        );

    -- SENSOR-INSTANTIATION: thermal_inst_0

end Behavioral;
