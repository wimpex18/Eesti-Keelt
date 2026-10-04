# Startup verification — DEV-18

Measured locally on 2026-10-03, with follow-up verification on 2026-10-04.
The public deployment has not received these fixes from this session.

## Changes

The container builds the existing ES-module graph with [esbuild](https://esbuild.github.io/api/).
It serves one minified script and minified CSS with prebuilt gzip variants.
Unhashed code URLs still revalidate; the service worker retains network-first
code, offline fallback and uncached APIs. Its compiled precache omits the
individual source modules, avoiding a second download of the same graph.
Ordinary source-checkout development continues serving editable modules.

The initial HTML contains the start choices and Russian skill glosses. A small
inline route selection paints the requested panel before module initialization.
Start buttons remain disabled until their handlers are installed. The restart
flow reuses this markup, so there is one source for the initial copy.

Self-hosted Geologica uses optional font display. Preloaded fonts can be used
at first paint; on a slow cold connection the fallback remains for that load,
avoiding a late font substitution. Cached Geologica is available on later loads.
Speech/evaluation/writing probes are deferred to their relevant screens.

## Matched cold-load timings

Chrome 154, native reload; service-worker bypass and HTTP cache disabled;
150 ms network latency, 204,800 bytes/s download, 96,000 bytes/s upload and
4× CPU slowdown for **both** viewports. There was no concurrent Lighthouse run
or active device toolbar during these measurements. Raw viewport dimensions
were checked after reload. Each before value is one sample; after values are
medians of three repeated loads of the compressed build.

| Viewport | First content before → after | Module initialization before → after |
|---|---|---|
| Desktop 1512×406 | 2.132 → 0.828 s | 3.063 → 1.151 s |
| Phone 390×844 | 2.220 → 0.812 s | 2.990 → 1.137 s |

First content is the browser's FCP. Initialization is the end of
DOMContentLoaded, after the module graph and synchronous UI bootstrap run;
it does not measure completion of every API, model call or lesson request.
After-sample ranges: desktop FCP 0.800–0.856 s and initialization
1.137–1.153 s; phone FCP 0.808–0.816 s and initialization 1.136–1.150 s.

Startup JavaScript requests fell from **24 to 1**. Resource Timing reports
362,209 → 73,739 transferred bytes including response headers, about an 80%
reduction. The CSS gzip response transfers about 18 KB. These timings were
captured before the final optional-font adjustment; the bundle and routing
are unchanged, and that adjustment is independently checked below.

## Mobile layout stability

Chrome DevTools Lighthouse 13.4.1, navigation/Mobile/Slow 4G on `#start`,
after clearing only the disposable local origin's storage:

| Retained build sample | FCP | CLS | TBT | Report scores: performance / accessibility / best practices / SEO |
|---|---|---|---|---|
| Compressed build with font swap | 1.6 s | 0.724 | 0 ms | 73 / 100 / 100 / 100 |
| Final optional-font build | 1.681 s | **0.003** | 0 ms | 96 / 100 / 100 / 100 |

The shift insight attributed 0.721 to the body and late Latin/Cyrillic web
fonts; the remaining small shift was skill navigation. Optional display keeps
the initially selected face stable. Earlier unbundled samples varied between
CLS 0.006 and 0.701; they are not a controlled causal baseline.

**Exclude Lighthouse LCP from the speed claim.** Its reported largest element
was the browser-control extension's cursor image. The extension warning also
limits interpretation of its aggregate performance score. The FCP/module
comparison above is the evidence for speed; the Lighthouse shift insight is
diagnostic evidence for the font change, not a real-device field percentile.
Later samples whose device toolbar reset the viewport/throttle were discarded.

## Reproduction and release check

1. Run `npm ci && npm run build:web`.
2. Start an isolated local guest with blank provider keys and scratch learner
   databases. Set `EESTI_WEB_BUILD=1` to preview the production assets.
3. For paired timing, disable HTTP caching, bypass the service worker, apply the
   fixed settings above and use native Reload. Keep the device toolbar off;
   verify viewport dimensions and network transfer timings after each load.
4. Run Lighthouse separately with its own device/network configuration. Clear
   only the disposable test origin; inspect the LCP element and CLS sources.
5. Run the full browser journeys against the compiled assets, inspect both
   viewports, then restore throttles/cache settings. CI now builds and tests this
   same asset path. Unit coverage checks gzip negotiation and offline precache.
6. After user merge/deployment, run deep production smoke and repeat on the
   public app. Local results do not establish Cloud Run wake-up or model latency.

Raw evidence remains ignored under `.impeccable/review/qa/`:
`fix-timing-before-{desktop,phone}.json`, `fix-repeat-timings.json`,
`fix-before-mobile.json`, `fix-after-mobile.json`, browser and Python logs.
