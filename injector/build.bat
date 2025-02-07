@echo off
setlocal enabledelayedexpansion

:: Find Visual Studio installation
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe`) do (
	set "MSBUILD=%%i"
)

if not defined MSBUILD (
	echo Error: MSBuild not found. Please install Visual Studio 2022 with C++ development tools.
	exit /b 1
)

:: Build the DLL
echo Building SanSync DLL...
"%MSBUILD%" SanSync.sln /p:Configuration=Release /p:Platform=x64 /v:m

if errorlevel 1 (
	echo Build failed!
	exit /b 1
)

:: Copy DLL to the correct location
if not exist "..\bin" mkdir "..\bin"
copy /Y "bin\Release\SanSync.dll" "..\bin\SanSync.dll"

echo Build completed successfully!