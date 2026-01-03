// Preload script for security
// This script runs before the web page loads and has access to both
// Node.js APIs and the web page's DOM

const { contextBridge } = require('electron');

// Expose protected methods that allow the renderer process to use
// specific Node.js features safely
contextBridge.exposeInMainWorld('electronAPI', {
    platform: process.platform,
    version: process.versions.electron
});

console.log('Preload script loaded successfully');
