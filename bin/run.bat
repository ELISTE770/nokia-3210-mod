@echo off

.\spd_dump ^
  fdl nor_fdl1.bin 0x40004000 ^
  fdl fpdoom.bin ram

if %ERRORLEVEL% neq 0 goto end

cd workdir && ..\libc_server -- --bright 50 --rotate 3 doom

:end
pause
