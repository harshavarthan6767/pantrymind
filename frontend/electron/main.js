import { app, BrowserWindow, ipcMain } from 'electron';
import { spawn } from 'child_process';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;
let pythonProcess = null;

const isDev = process.env.NODE_ENV === 'development';

/**
 * Wait for a TCP port to become available.
 * Polls every 500ms until the port responds or timeout is reached.
 */
function waitForPort(port, timeout = 45000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    const check = () => {
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode < 500) {
          resolve();
        } else {
          retry();
        }
        res.resume();
      });
      req.on('error', retry);
      req.setTimeout(800, () => { req.destroy(); retry(); });
    };

    const retry = () => {
      if (Date.now() - start > timeout) {
        reject(new Error(`Backend did not start within ${timeout}ms`));
      } else {
        setTimeout(check, 500);
      }
    };

    check();
  });
}

function startPythonBackend() {
  const rootDir = path.join(__dirname, '..', '..');
  const pythonExecutable = path.join(rootDir, '.venv', 'Scripts', 'python.exe');

  console.log('[Electron] Starting Python backend at:', pythonExecutable);

  pythonProcess = spawn(
    pythonExecutable,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: rootDir,
      env: { ...process.env, APP_ENV: isDev ? 'development' : 'production' },
    }
  );

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python Backend]: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    // Uvicorn writes startup logs to stderr — only log actual errors
    const msg = data.toString();
    if (msg.includes('ERROR') || msg.includes('Exception')) {
      console.error(`[Python Backend Error]: ${msg}`);
    } else {
      console.log(`[Python Backend]: ${msg}`);
    }
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Python Backend] exited with code ${code}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'PantryMind',
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    autoHideMenuBar: true,
    backgroundColor: '#0c0c10',
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    // Only open DevTools if explicitly requested
    // mainWindow.webContents.openDevTools();
  } else {
    const indexPath = path.join(__dirname, '..', 'dist', 'index.html');
    mainWindow.loadFile(indexPath);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  ipcMain.on('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.on('window-maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    }
  });

  ipcMain.on('window-close', () => {
    if (mainWindow) mainWindow.close();
  });
}

app.whenReady().then(async () => {
  startPythonBackend();

  // Show a loading splash while backend starts up
  const splash = new BrowserWindow({
    width: 360,
    height: 200,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    backgroundColor: '#00000000',
    webPreferences: { nodeIntegration: false },
  });

  splash.loadURL(`data:text/html,
    <html>
      <body style="margin:0;background:linear-gradient(135deg,#1a2a1e,#0c0c10);display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:#e8e8f0;border-radius:16px;">
        <div style="font-size:40px;margin-bottom:16px;">🌿</div>
        <div style="font-size:20px;font-weight:500;letter-spacing:0.02em;">PantryMind</div>
        <div style="margin-top:16px;font-size:12px;color:#6b8f71;letter-spacing:0.05em;">Starting backend...</div>
        <div style="margin-top:20px;width:120px;height:2px;background:rgba(255,255,255,0.1);border-radius:1px;overflow:hidden;">
          <div style="width:40%;height:100%;background:#6b8f71;border-radius:1px;animation:slide 1.2s ease-in-out infinite alternate;" id="bar"></div>
        </div>
        <style>@keyframes slide{from{margin-left:0}to{margin-left:60%}}</style>
      </body>
    </html>
  `);

  try {
    console.log('[Electron] Waiting for Python backend on port 8000...');
    await waitForPort(8000, 45000);
    console.log('[Electron] Backend ready! Loading app...');
  } catch (err) {
    console.error('[Electron] Backend startup timeout:', err.message);
    // Open app anyway — api.js retry logic will handle it
  }

  // Close splash, open main window
  createWindow();
  splash.close();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pythonProcess) {
    console.log('[Electron] Killing Python backend...');
    spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
  }
});
