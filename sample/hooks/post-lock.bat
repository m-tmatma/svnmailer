@echo off
REM post lock hook -- called if a file is locked by a user
REM This is a feature of SVN >= 1.2
REM
REM The mailer is put into the background in order to
REM leave the script faster (by the --background option)
REM
REM You need to adjust the config path, the python path,
REM and the path to svn-mailer if necessary.
REM
REM Note that the mailer also pulls STDIN in order to retrieve
REM the file names which were locked.

set CONFIG=C:\path\to\your\config
set MAILER=@@SCRIPTS@@\svn-mailer.py
set PYTHON=@@PYTHON@@


set REPOS=%1
set USER=%2

"%PYTHON%" "%MAILER%" --lock --config "%CONFIG%" --repository "%REPOS%" --author "%USER%" --background

