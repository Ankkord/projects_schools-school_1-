@echo off
pyinstaller -y --onefile --console --name="Skyris motor" --icon="S_logo.ico" --hidden-import=openpyxl --hidden-import=styleframe --collect-submodules=tkinter ui.py
