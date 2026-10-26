@echo off

.\spd_dump ^
  fdl t117_fdl1.bin 0x6200 ^
  fdl fpdoom.bin 0x801M

if %ERRORLEVEL% neq 0 goto end

cd workdir && ..\libc_server -- --bright 50 --rotate 3 doom

:end
pause
