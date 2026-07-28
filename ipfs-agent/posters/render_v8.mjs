import { chromium } from '/home/ubuntu/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs';

const HTML = 'file:///home/ubuntu/blogs/coded-blog/ipfs-agent/posters/esip_ipfs_poster_v8_landscape.html';

const browser = await chromium.launch();

// 96 dpi base PNG (4608x3456) + PDF
const page1 = await browser.newPage({ viewport: { width: 4608, height: 3456 }, deviceScaleFactor: 1 });
await page1.goto(HTML, { waitUntil: 'networkidle' });
await page1.screenshot({ path: 'esip_ipfs_poster_v8_landscape.png', clip: { x: 0, y: 0, width: 4608, height: 3456 } });
await page1.pdf({ path: 'esip_ipfs_poster_v8_landscape.pdf', width: '4614px', height: '3462px', printBackground: true, pageRanges: '1' });
await page1.close();

// 150 dpi PNG (7200x5400)
const page2 = await browser.newPage({ viewport: { width: 4608, height: 3456 }, deviceScaleFactor: 150 / 96 });
await page2.goto(HTML, { waitUntil: 'networkidle' });
await page2.screenshot({ path: 'esip_ipfs_poster_v8_landscape_150.png', clip: { x: 0, y: 0, width: 4608, height: 3456 } });
await page2.close();

await browser.close();
console.log('rendered v8: png, pdf, 150dpi png');
