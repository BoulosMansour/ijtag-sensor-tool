library IEEE;
use IEEE.std_logic_1164.all;

entity comp_a is
    generic (WIDTH : integer := 8);
    port (
        clk      : in  std_logic;
        data_in  : in  std_logic_vector(7 downto 0);
        data_out : out std_logic_vector(7 downto 0)
    );
end comp_a;

architecture rtl of comp_a is
begin
    process(clk)
    begin
        if rising_edge(clk) then
            data_out <= data_in;
        end if;
    end process;
end rtl;
