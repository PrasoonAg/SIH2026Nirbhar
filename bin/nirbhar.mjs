#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const cliTs = join(__dirname, '../src/cli.ts');

const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const child = spawn(cmd, ['-y', 'tsx', `"${cliTs}"`, ...process.argv.slice(2).map(a => `"${a}"`)], {
  stdio: 'inherit',
  shell: true,
  windowsVerbatimArguments: true
});

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
