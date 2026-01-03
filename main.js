const { app, BrowserWindow, dialog, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const kill = require('tree-kill');
const http = require('http');
const fs = require('fs');
const { autoUpdater } = require('electron-updater');

let mainWindow;
let pythonProcess;
let isQuitting = false; // Declare isQuitting globally
const FLASK_PORT = 5000;
const FLASK_URL = `http://localhost:${FLASK_PORT}`;

const isDev = !app.isPackaged;

// --- Auto Update Configuration ---
autoUpdater.autoDownload = false; // Ask user before downloading
autoUpdater.logger = require("electron-log");
autoUpdater.logger.transports.file.level = "info";

function getBackendPath() {
  if (isDev) {
    const venvPython = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
    return 'python';
  } else {
    return path.join(process.resourcesPath, 'meadoc_server', 'meadoc_server.exe');
  }
}

function getAppPath() {
  if (isDev) {
    return __dirname;
  } else {
    // In production, we don't need app.asar.unpacked for the backend anymore
    // as it is in resources/meadoc_server
    return process.resourcesPath;
  }
}

function logToFile(message) {
  try {
    const logPath = path.join(isDev ? __dirname : process.resourcesPath, 'debug.log');
    fs.appendFileSync(logPath, `${new Date().toISOString()} - ${message}\n`);
  } catch (e) {
    console.error('Failed to write log:', e);
  }
}

function startPythonBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = getBackendPath();
    const appPath = isDev ? __dirname : path.join(process.resourcesPath, 'meadoc_server');

    logToFile(`Starting Backend...`);
    logToFile(`Backend Path: ${backendPath}`);
    logToFile(`CWD: ${appPath}`);

    const env = Object.assign({}, process.env, {
      PYTHONUNBUFFERED: '1',
      FLASK_APP: 'app.py'
    });

    try {
      let args = [];
      if (isDev) {
        args = ['app.py'];
      }

      // Use pipe for stderr to capture errors
      pythonProcess = spawn(backendPath, args, {
        cwd: appPath,
        env: env,
        stdio: ['ignore', 'pipe', 'pipe']
      });

      pythonProcess.stdout.on('data', (data) => {
        logToFile(`[Backend STDOUT]: ${data.toString()}`);
      });

      pythonProcess.stderr.on('data', (data) => {
        logToFile(`[Backend STDERR]: ${data.toString()}`);
      });

      pythonProcess.on('error', (error) => {
        logToFile(`Failed to start backend process: ${error.message}`);
        console.error('Failed to start backend process:', error);
        reject(error);
      });

      pythonProcess.on('close', (code) => {
        logToFile(`Backend process exited with code ${code}`);
        console.log(`Backend process exited with code ${code}`);

        if (!isQuitting) {
          logToFile('Backend process crashed or closed unexpectedly. Restarting in 2 seconds...');
          setTimeout(() => {
            startPythonBackend();
          }, 2000);
        }
      });

      resolve();
    } catch (e) {
      logToFile(`Exception spawning process: ${e.message}`);
      reject(e);
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    show: true,
    backgroundColor: '#0f172a',
    icon: path.join(__dirname, 'meadocs.jpg'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'MeaDocs - AI-Powered Search'
  });

  mainWindow.setMenu(null);
  Menu.setApplicationMenu(null);

  // Load Flask URL directly - no loading screen
  mainWindow.loadURL(FLASK_URL);

  mainWindow.maximize();
  // mainWindow.webContents.openDevTools();

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle loading errors
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.log('Page failed to load, retrying...', errorDescription);
    setTimeout(() => {
      mainWindow.loadURL(FLASK_URL);
    }, 500);
  });
}

function checkServerAndLoad() {
  const tryConnect = () => {
    const req = http.get(FLASK_URL, (res) => {
      if (res.statusCode === 200) {
        console.log('Flask server is ready! Loading app...');
        if (mainWindow) {
          mainWindow.loadURL(FLASK_URL);
        }
      } else {
        console.log(`Server responded with ${res.statusCode}, retrying...`);
        setTimeout(tryConnect, 500);
      }
    });

    req.on('error', (e) => {
      console.log('Server not ready yet, retrying...');
      setTimeout(tryConnect, 500);
    });

    req.end();
  };

  tryConnect();
}

// --- Auto Update Events ---
autoUpdater.on('update-available', () => {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update Available',
    message: 'A new version of MeaDocs is available. Do you want to download it now?',
    buttons: ['Yes', 'No']
  }).then((result) => {
    if (result.response === 0) {
      autoUpdater.downloadUpdate();
    }
  });
});

autoUpdater.on('update-downloaded', () => {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update Ready',
    message: 'Update downloaded. The application will restart to install the update.',
    buttons: ['Restart']
  }).then(() => {
    autoUpdater.quitAndInstall();
  });
});

autoUpdater.on('error', (err) => {
  logToFile(`Auto-update error: ${err.message}`);
});

app.whenReady().then(async () => {
  try {
    console.log('Starting MeaDocs application...');

    startPythonBackend().catch(err => {
      console.error('Failed to start Python backend:', err);
    });

    createWindow();
    checkServerAndLoad();

    // Check for updates after 3 seconds
    if (!isDev) {
      setTimeout(() => {
        autoUpdater.checkForUpdatesAndNotify();
      }, 3000);
    }

  } catch (error) {
    console.error('Error starting application:', error);
    dialog.showErrorBox('Startup Error', error.message);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', (event) => {
  isQuitting = true; // Set the flag when the app is quitting
  if (pythonProcess) {
    console.log('Terminating Python process...');
    kill(pythonProcess.pid, 'SIGTERM', (err) => {
      if (err) {
        console.error('Error killing Python process:', err);
        kill(pythonProcess.pid, 'SIGKILL');
      }
    });
    pythonProcess = null;
  }
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  logToFile(`Uncaught Exception: ${error.message}`);
});