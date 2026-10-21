#!/usr/bin/env node
// Site preview video: hero -> circular cursor sweep (parallax) -> smooth wheel scroll to the footer with pauses at sections -> MP4.
// Requires: Node 18+, `playwright-core` or `playwright` resolvable from the current working directory, ffmpeg on PATH.
// Browser: --chrome <path> or env CHROME_PATH (e.g. chrome-headless-shell); otherwise Playwright's bundled Chromium.
// Always a temporary profile; never point it at a real user profile.
//
// node record_preview.mjs --url http://127.0.0.1:4321/ --out <dir> [--w 1440 --h 900] [--stops "[data-rx],.section"]
//   [--step 40] [--hero-ms 2600] [--pause-ms 700] [--no-sweep] [--dark] [--cpu] [--angle <backend>] [--chrome <path>]
//   [--crf 20] [--keep-frames] [--init-js "<code run before page scripts>"]
// --angle: WebGL backend for GPU runs (default: let Chromium choose; e.g. d3d11 on Windows, metal on macOS, vulkan/gl on Linux).
// --cpu: SwiftShader software WebGL (no GPU needed, but slow and choppy).
// Exit: 0 ok; 3 video written but the page logged console errors; 1 failure (scroll stalled, no frames, ffmpeg);
//   64 bad arguments (including an invalid --stops selector); 69 no browser / playwright not found.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const args = process.argv.slice(2);
const FLAGS = ['no-sweep', 'dark', 'keep-frames', 'cpu', 'help'];
const VALS = ['url', 'out', 'w', 'h', 'stops', 'step', 'hero-ms', 'pause-ms', 'crf', 'init-js', 'chrome', 'angle'];
const opt = { w: 1440, h: 900, step: 40, 'hero-ms': 2600, 'pause-ms': 700, crf: 20, stops: '' };
const usage = () => {
  const head = fs.readFileSync(new URL(import.meta.url), 'utf8').split('\n').slice(1, 13).map((l) => l.replace(/^\/\/ ?/, ''));
  console.log(head.join('\n'));
};
const bad = (msg) => { console.error(`${msg} (run with --help)`); process.exit(64); };
for (let i = 0; i < args.length; i++) {
  const k = args[i].replace(/^--/, '');
  if (FLAGS.includes(k)) opt[k] = true;
  else if (VALS.includes(k)) {
    if (i + 1 >= args.length || args[i + 1].startsWith('--')) bad(`--${k} needs a value`);
    opt[k] = args[++i];
  } else bad(`unknown argument ${args[i]}`);
}
if (opt.help) { usage(); process.exit(0); }
if (!opt.url || !opt.out) bad('--url and --out are required');
// numbers: [min, max], validated before any file operation
const RANGE = { w: [320, 3840], h: [320, 2160], step: [5, 2000], 'hero-ms': [0, 60000], 'pause-ms': [0, 10000], crf: [0, 51] };
for (const [k, [lo, hi]] of Object.entries(RANGE)) {
  const v = Number(opt[k]);
  if (!Number.isInteger(v) || v < lo || v > hi) bad(`--${k} must be an integer ${lo}..${hi}`);
  opt[k] = v;
}
if (opt.angle && !/^[a-z0-9-]+$/i.test(opt.angle)) bad('--angle must be a backend name such as d3d11, metal, vulkan, gl');
const W = opt.w, H = opt.h;
const out = path.resolve(opt.out);

let chromium;
const req = createRequire(path.join(process.cwd(), 'noop.js'));
for (const mod of ['playwright-core', 'playwright']) {
  try { ({ chromium } = req(mod)); break; } catch { /* try next */ }
}
if (!chromium) { console.error('playwright-core / playwright not found from the current directory: npm i -D playwright-core'); process.exit(69); }
const exe = opt.chrome || process.env.CHROME_PATH || undefined;
if (exe && !fs.existsSync(exe)) { console.error(`browser not found: ${exe}`); process.exit(69); }

const gpuArgs = opt.cpu
  ? ['--enable-unsafe-swiftshader', '--use-angle=swiftshader']
  : ['--enable-gpu', '--ignore-gpu-blocklist', ...(opt.angle ? [`--use-angle=${opt.angle}`] : [])];
let browser;
try {
  browser = await chromium.launch({ executablePath: exe, headless: true, args: ['--autoplay-policy=no-user-gesture-required', ...gpuArgs] });
} catch (e) {
  console.error(`browser launch failed: ${e.message.split('\n')[0]} (set --chrome / CHROME_PATH or run: npx playwright install chromium)`);
  process.exit(69);
}
const errs = [];
const frames = [];
let stops = [];
let stalled = '', badStops = '';
let stopT = 0;
try {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, colorScheme: opt.dark ? 'dark' : 'light' });
  if (opt['init-js']) await ctx.addInitScript(opt['init-js']);
  const page = await ctx.newPage();
  page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
  page.on('pageerror', (e) => errs.push(e.message));

  const cdp = await ctx.newCDPSession(page);
  cdp.on('Page.screencastFrame', (f) => {
    frames.push({ t: f.metadata.timestamp, d: f.data });
    cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 88, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
  await page.goto(opt.url, { waitUntil: 'load' });
  await page.mouse.move(W / 2, H / 2);
  await page.waitForTimeout(opt['hero-ms']);
  if (!opt['no-sweep']) {
    for (let i = 0; i <= 40; i++) {
      const a = (i / 40) * Math.PI * 2;
      await page.mouse.move(W / 2 + Math.cos(a) * W * 0.3, H / 2 + Math.sin(a) * H * 0.2);
      await page.waitForTimeout(35);
    }
    await page.mouse.move(W / 2, H / 2);
  }
  // the whole selector list in one querySelectorAll (commas inside :is() stay intact); all matches, ascending, deduplicated
  const sel = String(opt.stops).trim();
  if (sel) {
    try {
      stops = await page.evaluate((s) => [...new Set([...document.querySelectorAll(s)].map((e) =>
        Math.round(e.getBoundingClientRect().top + scrollY)))].sort((a, b) => a - b), sel);
    } catch (e) { badStops = `invalid --stops: ${e.message.split('\n')[0]}`; }
  }
  const done = new Set();
  let still = 0, last = -1, reached = false;
  for (let guard = 0; !badStops && guard < 20000; guard++) {
    // re-read the height every step: pins and lazy sections change it while scrolling
    const [cur, end] = await page.evaluate(() => [scrollY, document.documentElement.scrollHeight - innerHeight]);
    if (cur >= end - 4) { reached = true; break; }
    still = Math.abs(cur - last) < 1 ? still + 1 : 0;
    last = cur;
    if (still >= 100) { stalled = `scroll stalled at ${Math.round(cur)} of ${Math.round(end)} px`; break; }
    const s = stops.find((y) => !done.has(y) && cur >= y - 10);
    if (s != null) { done.add(s); await page.waitForTimeout(opt['pause-ms']); }
    await page.mouse.wheel(0, Math.min(opt.step, end - cur));
    await page.waitForTimeout(30);
  }
  if (!reached && !stalled && !badStops) stalled = 'end of page not reached within 20000 steps';
  await page.waitForTimeout(1800);
  stopT = Date.now() / 1000; // screencast frame timestamps are epoch seconds too
  await cdp.send('Page.stopScreencast');
  await ctx.close();
} finally {
  await browser.close().catch(() => {});
}

if (badStops) { console.error(badStops); process.exit(64); }
if (stalled) { console.error(stalled); process.exit(1); }
if (frames.length < 2) { console.error('no frames: the page did not render'); process.exit(1); }
fs.mkdirSync(out, { recursive: true });
// a private temp frames folder per run: other files in <out> are never touched, only this folder is removed
const framesDir = fs.mkdtempSync(path.join(out, 'frames-'));
const fail = (msg) => {
  console.error(msg);
  if (!opt['keep-frames']) fs.rmSync(framesDir, { recursive: true, force: true });
  process.exit(1);
};
let list = '';
frames.forEach((f, i) => {
  const n = `f${String(i).padStart(5, '0')}.jpg`;
  fs.writeFileSync(path.join(framesDir, n), Buffer.from(f.d, 'base64'));
  const dur = i + 1 < frames.length ? frames[i + 1].t - f.t : 0.04;
  list += `file '${n}'\nduration ${dur.toFixed(4)}\n`;
});
fs.writeFileSync(path.join(framesDir, 'list.txt'), list);
// hold the last frame until recording stopped (a static footer sends no new frames); the concat demuxer ignores
// the duration of the last entry, so the hold is added with tpad
const hold = Math.max(0.04, stopT - frames.at(-1).t).toFixed(3);
const mp4 = path.join(out, 'preview.mp4');
const ff = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'list.txt',
  '-fps_mode', 'vfr', '-vf', `fps=30,tpad=stop_mode=clone:stop_duration=${hold},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p`,
  '-c:v', 'libx264', '-preset', 'slow', '-crf', String(opt.crf), '-movflags', '+faststart', mp4],
  { cwd: framesDir, encoding: 'utf8', windowsHide: true });
if (ff.status !== 0) fail(`ffmpeg: ${ff.stderr || ff.error}`);
if (!opt['keep-frames']) fs.rmSync(framesDir, { recursive: true, force: true });
const receipt = {
  url: opt.url, mp4, bytes: fs.statSync(mp4).size, frames: frames.length,
  seconds: +(Math.max(stopT, frames.at(-1).t) - frames[0].t).toFixed(1), viewport: `${W}x${H}`,
  browser: exe ? path.basename(exe) : 'playwright-chromium', gpu: opt.cpu ? 'swiftshader' : (opt.angle || 'auto'),
  stops, console_errors: errs,
};
fs.writeFileSync(path.join(out, 'preview.json'), JSON.stringify(receipt, null, 1));
console.log(JSON.stringify(receipt));
process.exit(errs.length ? 3 : 0);
