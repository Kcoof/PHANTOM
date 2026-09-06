import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('phantom', {
  desktop: true,
  version: process.env.npm_package_version ?? '1.0.0',
})
