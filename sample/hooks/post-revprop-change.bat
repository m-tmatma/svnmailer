@echo off
REM post revprop change hook -- called for revision property changes
REM like svn:log, svn:author, etc. Modifying revision properties will
REM only work if the pre-revprop-change hook is properly configured.
REM
REM The mailer is put into the background in order to
REM leave the script faster (by the --background option)
REM
REM You need to adjust the config path, the python path,
REM and the path to svn-mailer if necessary.
REM
REM If you're using SVN 1.2 or later you may use the second commandline
REM variant (see below) which uses the ACTION variable and pulls STDIN in
REM order to provide revision property diffs.

set CONFIG=C:\path\to\your\config
set MAILER=@@SCRIPTS@@\svn-mailer.py
set PYTHON=@@PYTHON@@


set REPOS=%1
set REV=%2
set USER=%3
set PROPNAME=%4
set ACTION=%5

REM command line for SVN < 1.2 (works with >= 1.2 as well)
"%PYTHON%" "%MAILER%" --propchange --config "%CONFIG%" --repository "%REPOS%" --revision "%REV%" --author "%USER%" --propname "%PROPNAME%" --background

REM command line for SVN >= 1.2 (uses new features)
REM "%PYTHON%" "%MAILER%" --propchange --config "%CONFIG%" --repository "%REPOS%" --revision "%REV%" --author "%USER%" --propname "%PROPNAME%" --action "%ACTION%" --background

