' Runs the local Gmail polling batch file hidden for Windows Task Scheduler.
' It does not contain credentials, tokens, or secrets.
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batchPath = fso.BuildPath(scriptDir, "run_gmail_poll_once.bat")
shell.Run Chr(34) & batchPath & Chr(34), 0, True
