library IEEE;
use IEEE.std_logic_1164.all;

entity comp_b is
    port (
        data_in : in  std_logic_vector(7 downto 0);
        result  : out std_logic
    );
end comp_b;

architecture rtl of comp_b is
begin
    result <= or data_in;
end rtl;
