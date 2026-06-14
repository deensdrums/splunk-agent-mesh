/* eslint-disable */

const path = require('path');
const shell = require('shelljs');
const OS = require('os').platform().toLocaleLowerCase();

const arg = process.argv[2];
const commands = ['build', 'link'];

if (!arg) {
    shell.echo(
        `No command received, please supply a command to run. \nCommands: ${commands.join(', ')}`
    );
    shell.exit(1);
}

if (!commands.includes(arg)) {
    shell.echo(`Please supply one of the following command to run: ${commands.join(', ')}`);
    shell.exit(1);
}

const PKG_DIR = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(PKG_DIR, '..', '..');
const APP_NAME = 'splunk-agent-mesh';

function packageTgz() {
    const stageDir = path.join(PKG_DIR, 'stage');
    const targetDir = path.join(REPO_ROOT, 'target');
    const scratchDir = path.join(targetDir, '_pkg');
    const appCopyDir = path.join(scratchDir, APP_NAME);
    const tgzPath = path.join(targetDir, 'app.tgz');

    shell.mkdir('-p', targetDir);
    shell.rm('-rf', scratchDir);
    shell.mkdir('-p', appCopyDir);
    shell.cp('-R', path.join(stageDir, '*'), appCopyDir);

    const result = shell.exec(`tar czf "${tgzPath}" -C "${scratchDir}" "${APP_NAME}"`);
    shell.rm('-rf', scratchDir);

    if (result.code !== 0) {
        shell.echo('Failed to create app.tgz');
        shell.exit(1);
    }
    shell.echo(`Packaged ${tgzPath}`);
}

// prettier-ignore
const runCommands = {
    win32: {
        build: () => shell.exec('set NODE_ENV=production&&.\\node_modules\\.bin\\webpack --mode=production'),
        link: () => shell.exec('mklink /D "%SPLUNK_HOME%\\etc\\apps\\splunk-agent-mesh" "%cd%\\stage"'),
    },
    nix: {
        build: () => shell.exec('export NODE_ENV=production && ./node_modules/.bin/webpack --mode=production'),
        link: () => shell.exec('ln -s $PWD/stage $SPLUNK_HOME/etc/apps/splunk-agent-mesh'),
    },
};

try {
    const isWindows = OS === 'win32' || OS === 'win64';
    const os = isWindows ? 'win32' : 'nix';
    runCommands[os][arg]();
    if (arg === 'build') {
        packageTgz();
    }
} catch (error) {
    shell.echo(error);
}
