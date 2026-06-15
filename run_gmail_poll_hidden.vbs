Set WshShell = CreateObject("WScript.Shell")

ProjectDir = "D:\cyberproject\ai-supported-cyber-project"
BatFile = ProjectDir & "\run_gmail_poll_once.bat"

WshShell.CurrentDirectory = ProjectDir
WshShell.Run """" & BatFile & """", 0, False
