' Scrinium starter - launches without a console window.
' Prefers the bundled exe, falls back to pythonw.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

sh.Environment("PROCESS")("PYTHONPATH") = ""

If fso.FileExists(dir & "dist\Scrinium.exe") Then
    sh.Run Chr(34) & dir & "dist\Scrinium.exe" & Chr(34), 0, False
ElseIf fso.FileExists(dir & "Scrinium.exe") Then
    sh.Run Chr(34) & dir & "Scrinium.exe" & Chr(34), 0, False
Else
    main = dir & "main.pyw"
    sysPy = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe")
    If fso.FileExists(sysPy) Then
        sh.Run Chr(34) & sysPy & Chr(34) & " " & Chr(34) & main & Chr(34), 0, False
    Else
        sh.Run "pythonw " & Chr(34) & main & Chr(34), 0, False
    End If
End If