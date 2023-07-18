# Define the download URL and file path
$installerUrl = "https://go.microsoft.com/fwlink/?linkid=2239549"
$installerPath = "$env:TEMP\msodbcsql.msi"

# Download the ODBC Driver installer
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

# Install the ODBC Driver silently
Start-Process -Filepath "msiexec.exe" -ArgumentList "/i $installerPath /qr IACCEPTMSODBCSQLLICENSETERMS=YES"

# Start-Process -FilePath msiexec -ArgumentList "/i $installerPath /passive /qn" -Wait
# Start-Process -Filepath "msiexec.exe" -ArgumentList "/i msodbcsql.msi /qr IACCEPTMSODBCSQLLICENSETERMS=YES"

# Clean up the temporary installer file
Remove-Item $installerPath