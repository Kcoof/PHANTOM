/**
 * PHANTOM desktop shell — spawns the Python backend, loads the built frontend,
 * and tears everything down on quit (plan.md Part 2 / quickstart Scenario I).
 */
import { spawn, ChildProcess } from 'node:child_process'
import { app, BrowserWindow, shell } from 'electron'
import path from 'node:path'
import fs from 'node:fs'
import net from 'node:net'

let backendProcess: ChildProcess | null = null
let mainWindow: BrowserWindow | null = null

const BACKEND_PORT = 8899
const DEV_URL = 'http://localhost:5173'
const isDev = !app.isPackaged

function resolveBackendCommand(): { cmd: string; args: string[]; cwd: string } | null {
  const repoRoot = isDev ? path.join(__dirname, '..') : process.resourcesPath
  const backendDir = path.join(repoRoot, 'backend')
  const venvPython = path.join(backendDir, '.venv', 'Scripts', process.platform === 'win32' ? 'python.exe' : 'python')
  if (fs.existsSync(venvPython)) {
    return { cmd: venvPython, args: ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], cwd: backendDir }
  }
  if (fs.existsSync(path.join(backendDir, '.venv', 'bin', 'python'))) {
    return { cmd: path.join(backendDir, '.venv', 'bin', 'python'), args: ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], cwd: backendDir }
  }
  // fall back to system python (documented setup)
  return { cmd: process.platform === 'win32' ? 'python' : 'python3', args: ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], cwd: backendDir }
}

function startBackend(): void {
  if (backendProcess) return
  const resolved = resolveBackendCommand()
  if (!resolved) return
  backendProcess = spawn(resolved.cmd, resolved.args, {
    cwd: resolved.cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })
  backendProcess.stdout?.on('data', (d: Buffer) => console.log(`[backend] ${d}`))
  backendProcess.stderr?.on('data', (d: Buffer) => console.error(`[backend] ${d}`))
  backendProcess.on('exit', (code) => {
    console.log(`[backend] exited ${code}`)
    backendProcess = null
  })
}

function stopBackend(): void {
  if (!backendProcess) return
  const proc = backendProcess
  backendProcess = null
  try {
    if (process.platform === 'win32') {
      // kill the process tree (uvicorn may spawn workers)
      spawn('taskkill', ['/pid', String(proc.pid), '/f', '/t'], { windowsHide: true })
    } else {
      proc.kill('SIGTERM')
    }
  } catch (err) {
    console.error('[backend] stop failed', err)
  }
}

function waitForBackend(retries = 40): Promise<void> {
  return new Promise((resolve, reject) => {
    const attempt = (left: number) => {
      const socket = net.connect({ host: '127.0.0.1', port: BACKEND_PORT })
      socket.once('connect', () => {
        socket.destroy()
        resolve()
      })
      socket.once('error', () => {
        socket.destroy()
        if (left <= 0) reject(new Error('backend did not come up'))
        else setTimeout(() => attempt(left - 1), 500)
      })
    }
    attempt(retries)
  })
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 640,
    backgroundColor: '#0a0a0f',
    title: 'PHANTOM',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }: { url: string }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  if (isDev) {
    void mainWindow.loadURL(DEV_URL)
  } else {
    void mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(async () => {
  startBackend()
  try {
    await waitForBackend()
  } catch (err) {
    console.error('[phantom] backend unavailable, loading UI anyway:', err)
  }
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  app.quit()
})

app.on('before-quit', () => {
  stopBackend()
})
