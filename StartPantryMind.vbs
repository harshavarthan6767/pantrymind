Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\pantrymind-desktop - Copy"
WshShell.Run """E:\pantrymind-desktop - Copy\StartPantryMind.bat""", 1, False
