Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\pantrymind-desktop\frontend"
WshShell.Run "cmd /c npm run electron:dev", 0, False
