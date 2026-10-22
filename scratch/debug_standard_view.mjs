import { spawn } from 'child_process';

const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
    '--headless=new',
    '--remote-debugging-port=9233',
    '--window-size=1440,900',
    '--user-data-dir=/tmp/cdp_profile_' + Date.now(),
    'about:blank'
]);

await new Promise(r => setTimeout(r, 1200));

try {
    const tabsRes = await fetch('http://127.0.0.1:9233/json');
    const tabs = await tabsRes.json();
    const ws = new WebSocket(tabs[0].webSocketDebuggerUrl);

    await new Promise(resolve => ws.onopen = resolve);

    let id = 1;
    function send(method, params = {}) {
        return new Promise(resolve => {
            const curId = id++;
            const handler = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.id === curId) {
                    ws.removeEventListener('message', handler);
                    resolve(msg.result);
                }
            };
            ws.addEventListener('message', handler);
            ws.send(JSON.stringify({ id: curId, method, params }));
        });
    }

    await send('Runtime.enable');
    await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride', {
        width: 1440,
        height: 900,
        deviceScaleFactor: 1,
        mobile: false
    });

    await send('Page.navigate', { url: 'http://127.0.0.1:5000/tournaments/test-tournament/categories/2' });
    await new Promise(r => setTimeout(r, 1500));

    // Force standard view (remove bracket-compact)
    const stdResult = await send('Runtime.evaluate', {
        expression: `(() => {
            const bracket = document.querySelector('.bracket');
            bracket.classList.remove('bracket-compact');
            renderBracketConnectors();

            const svg = document.querySelector('.bracket-svg-connectors');
            const paths = Array.from(document.querySelectorAll('.bracket-connector-path'));
            const r1 = document.querySelector('.bracket-round.round-1');
            const r2 = document.querySelector('.bracket-round.round-2');
            
            const r1c0 = r1.querySelector('.tennis-match');
            const r1c1 = r1.querySelectorAll('.tennis-match')[1];
            const r2c0 = r2.querySelector('.tennis-match');

            const bRect = bracket.getBoundingClientRect();
            const sRect = svg.getBoundingClientRect();

            return {
                isCompact: bracket.classList.contains('bracket-compact'),
                bracket: {
                    scrollWidth: bracket.scrollWidth,
                    scrollHeight: bracket.scrollHeight,
                    clientWidth: bracket.clientWidth,
                    clientHeight: bracket.clientHeight,
                    rect: bRect
                },
                svg: {
                    widthAttr: svg.getAttribute('width'),
                    heightAttr: svg.getAttribute('height'),
                    viewBox: svg.getAttribute('viewBox'),
                    rect: sRect,
                    styleWidth: svg.style.width,
                    styleHeight: svg.style.height
                },
                r1c0: r1c0.getBoundingClientRect(),
                r1c1: r1c1.getBoundingClientRect(),
                r2c0: r2c0.getBoundingClientRect(),
                pathsCount: paths.length,
                paths: paths.slice(0, 4).map(p => ({
                    d: p.getAttribute('d'),
                    stroke: window.getComputedStyle(p).stroke,
                    strokeWidth: window.getComputedStyle(p).strokeWidth,
                    display: window.getComputedStyle(p).display,
                    visibility: window.getComputedStyle(p).visibility,
                    bbox: p.getBBox ? p.getBBox() : null
                }))
            };
        })()`,
        returnByValue: true
    });

    console.log(JSON.stringify(stdResult.result.value, null, 2));

    ws.close();
} catch (e) {
    console.error(e);
} finally {
    chrome.kill();
}
