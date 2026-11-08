# Open Haiyan's updated system in VS Code on Windows

Install Git, Python 3.11 (with **Add python.exe to PATH**), Node.js LTS, Google
Chrome, and Visual Studio Code. Restart VS Code after installing prerequisites.

## Get the updated branch

In PowerShell or a VS Code terminal, from the folder where you keep projects:

```powershell
git clone --branch update-ui-ux https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan.git Haiyan-version-control
cd Haiyan-version-control
code .
```

If you already have this fork on your computer, open its folder in VS Code and
run these commands instead. Save or commit your own edits before updating:

```powershell
git switch update-ui-ux
git pull --ff-only
```

The updates are on `update-ui-ux`, so cloning the default `main` branch alone will
show the older application.

## Run from VS Code

1. Choose **Terminal → Run Task → DeFaketive: Setup (first run)**. Wait for setup
   to finish, then press a key if prompted. This installs dependencies and loads
   the included starter reports into an empty local database. Run it once per PC.
2. Choose **Terminal → Run Task → DeFaketive: Start**. The app builds the latest
   source when necessary and opens your browser when it is ready.
3. Visit **http://localhost:5173** for the updated app. The admin interface is at
   **http://localhost:5175**; its account is managed separately by the project's
   admin tooling.

You can also run the same scripts directly in the VS Code terminal:

```powershell
.\setup.cmd
.\start.cmd
```

Keep the app terminal and the separate **DeFaketive server (keep open)** window
open while using the system. Close the app/server windows when finished. If a
port is already in use, stop the existing app before starting another copy.

To edit with live browser updates, stop the running app first and choose
**DeFaketive: Develop (live updates)** instead, or run `.\dev.cmd`.

`localhost` refers to your own Windows computer. These addresses work after you
start the app there; running a server in a separate cloud workspace does not
start it on your PC. Accounts and scan history are also local to that installation.
