@echo off
REM post commit hook -- called for normal commits
REM
REM The mailer is put into the background in order to
REM leave the script faster (by the --background option)
REM
REM You need to adjust the config path, the python path,
REM and the path to svn-mailer if necessary.

set CONFIG=C:\path\to\your\config
set MAILER=@@SCRIPTS@@\svn-mailer.py
set PYTHON=@@PYTHON@@


set REPOS=%1
set REV=%2

"%PYTHON%" "%MAILER%" --commit --config "%CONFIG%" --repository "%REPOS%" --revision "%REV%" --background

