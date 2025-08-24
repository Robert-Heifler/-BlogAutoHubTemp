@echo off
cd /d C:\A_PROJECT

:: Get date in YYYY-MM-DD format (works with different regional settings)
for /f "tokens=2 delims==" %%I in ('wmic os get LocalDateTime /value') do set ldt=%%I
set datetime=%ldt:~0,4%-%ldt:~4,2%-%ldt:~6,2%_%ldt:~8,2%-%ldt:~10,2%-%ldt:~12,2%

git add .
git commit -m "Auto commit %datetime%"
git push

pause

