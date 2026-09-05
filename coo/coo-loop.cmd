@echo off
REM Windows runner for Task Scheduler.
REM Task Scheduler action: wscript.exe "C:\Users\lkmot\factory-context\code\fleet-triage\coo\run-hidden.vbs"
REM (runs one cycle per trigger; schedule the TRIGGER every 15 min, not an internal sleep loop)
"C:\Program Files\Git\bin\bash.exe" -lc "cd /c/Users/lkmot/factory-context/code/fleet-triage && ./coo/coo-loop.sh"
