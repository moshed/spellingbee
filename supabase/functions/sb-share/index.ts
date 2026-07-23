// Per-puzzle share preview for Spelling Bee.
//   ?l=<letters>&c=<center>&r=<room>  -> HTML with per-puzzle OG tags + redirect into the game
//   &img=1                            -> a PNG of that puzzle's flower (used as og:image)
// Deployed to the Misc project. Public (no JWT).
import { initWasm, Resvg } from 'https://esm.sh/@resvg/resvg-wasm@2.6.2'

const WASM_URL = 'https://unpkg.com/@resvg/resvg-wasm@2.6.2/index_bg.wasm'
const FONT_URL = 'https://cdn.jsdelivr.net/npm/@expo-google-fonts/inter@0.2.3/Inter_700Bold.ttf'
const GAME = 'https://spellingbee.dancykier.com/'
// public URL of this function (the proxy hides /functions/v1 from req.url, so pin it)
const SELF = 'https://atqhfbaurrmivjarowco.supabase.co/functions/v1/sb-share'

let wasmInit: Promise<void> | null = null
let fontData: Uint8Array | null = null
async function ready() {
  if (!wasmInit) wasmInit = initWasm(fetch(WASM_URL))
  await wasmInit
  if (!fontData) fontData = new Uint8Array(await (await fetch(FONT_URL)).arrayBuffer())
}

const clean = (s: string | null) => (s || '').replace(/[^a-z]/gi, '').toLowerCase()
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!))

function flowerSVG(letters: string, center: string) {
  const W = 1200, H = 630, R = 74, S = 1.06
  const Wd = 2 * R, Hh = R * Math.sqrt(3), cx = 360, cy = H / 2
  const dx = 0.75 * Wd * S, dyd = 0.5 * Hh * S, dyt = Hh * S
  const outer = [...letters].filter((l) => l !== center)
  const cells: [string, number, number, boolean][] = [
    [center, 0, 0, true], [outer[0] || '', 0, -dyt, false], [outer[1] || '', dx, -dyd, false],
    [outer[2] || '', dx, dyd, false], [outer[3] || '', 0, dyt, false], [outer[4] || '', -dx, dyd, false], [outer[5] || '', -dx, -dyd, false],
  ]
  const hexPts = (px: number, py: number) =>
    [0, 60, 120, 180, 240, 300].map((a) => {
      const rad = (a * Math.PI) / 180
      return `${(px + R * Math.cos(rad)).toFixed(1)},${(py + R * Math.sin(rad)).toFixed(1)}`
    }).join(' ')
  let g = ''
  for (const [ch, ox, oy, cen] of cells) {
    g += `<polygon points="${hexPts(cx + ox, cy + oy)}" fill="${cen ? '#f7da21' : '#e8ebf2'}"/>`
    if (ch) g += `<text x="${(cx + ox).toFixed(1)}" y="${(cy + oy + 18).toFixed(1)}" font-size="52" font-weight="700" text-anchor="middle" fill="#141414" font-family="Inter">${ch.toUpperCase()}</text>`
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="#0f1115"/>${g}<text x="720" y="290" font-size="84" font-weight="700" fill="#f4f6fb" font-family="Inter">Spelling</text><text x="720" y="386" font-size="84" font-weight="700" fill="#f7da21" font-family="Inter">Bee</text><text x="722" y="452" font-size="30" font-weight="700" fill="#9aa4b6" font-family="Inter">How many words can you make?</text></svg>`
}

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const l = clean(url.searchParams.get('l'))
  const c = clean(url.searchParams.get('c')).slice(0, 1)
  const r = (url.searchParams.get('r') || '').replace(/[^a-z0-9]/gi, '')

  if (url.searchParams.get('img') === '1') {
    try {
      await ready()
      const svg = flowerSVG(l || 'speling', c || (l ? l[0] : 's'))
      const resvg = new Resvg(svg, {
        fitTo: { mode: 'width', value: 1200 },
        font: { fontBuffers: [fontData!], defaultFontFamily: 'Inter', loadSystemFonts: false },
      })
      const png = resvg.render().asPng()
      return new Response(png, { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=604800' } })
    } catch (e) {
      return new Response('img error: ' + e, { status: 500 })
    }
  }

  const game = GAME + '#l=' + l + '&c=' + c + (r ? '&r=' + r : '')
  const img = SELF + '?img=1&l=' + l + '&c=' + c
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spelling Bee</title>
<meta property="og:type" content="website">
<meta property="og:title" content="Spelling Bee">
<meta property="og:description" content="Can you beat my score in this word puzzle?">
<meta property="og:image" content="${esc(img)}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="${esc(img)}">
<meta http-equiv="refresh" content="0;url=${esc(game)}">
</head><body style="background:#0f1115;color:#f4f6fb;font-family:sans-serif;text-align:center;padding:48px">
Opening Spelling Bee… <a style="color:#f7da21" href="${esc(game)}">tap to play</a>
<script>location.replace(${JSON.stringify(game)})</script></body></html>`
  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=3600' } })
})
