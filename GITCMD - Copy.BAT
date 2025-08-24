@echo off
cd /d C:\A_PROJECT
echo Changing directory to C:\A_PROJECT

git add .
echo Added all changes

git commit -m "Auto commit %datetime%"
echo Commit done

git push
echo Push completed

pause

