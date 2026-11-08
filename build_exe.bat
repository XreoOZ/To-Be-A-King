@echo off
echo ====================================================
echo Building Standalone Executable (.exe) with PyInstaller
echo ====================================================
pyinstaller --noconfirm --onedir --windowed ^
    --name "CK2Lite" ^
    --add-data "assets;assets" ^
    --add-data "data;data" ^
    main.py

echo.
echo Copying assets and data folders into dist\CK2Lite...
xcopy /E /I /Y assets dist\CK2Lite\assets
xcopy /E /I /Y data dist\CK2Lite\data
xcopy /E /I /Y assets dist\CK2Lite\_internal\assets
xcopy /E /I /Y data dist\CK2Lite\_internal\data

echo.
echo ====================================================
echo Build finished! Check the dist\CK2Lite\ folder.
echo You can run dist\CK2Lite\CK2Lite.exe directly.
echo ====================================================
pause
