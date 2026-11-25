import * as sdk from '@hermes/plugin-sdk'
import { createElement as h, useEffect, useRef, useState, useSyncExternalStore } from 'react'

const { host, ROUTES_AREA, SIDEBAR_NAV_AREA, SandboxedFrame } = sdk
const PATH = '/grounded-news'
const COVERAGE_VIEWS = ['Overview', 'Articles', 'Bias', 'Factuality', 'Ownership']
const SIDES = [
  ['Left', 'leftPercent', 'leftSrcCount'],
  ['Center', 'centerPercent', 'cntrSrcCount'],
  ['Right', 'rightPercent', 'rightSrcCount'],
]
const BIASES = {
  farLeft: 'Far left', left: 'Left', leanLeft: 'Lean left',
  center: 'Center', leanRight: 'Lean right', right: 'Right', farRight: 'Far right',
}
const RATING_LABELS = {
  veryLow: 'Very low', low: 'Low', mixed: 'Mixed', high: 'High', veryHigh: 'Very high',
  unknown: 'Unknown', telecom: 'Telecom', privateEquity: 'Private equity',
  mediaConglomerate: 'Media conglomerate', billionaire: 'Billionaire', government: 'Government',
  independent: 'Independent', other: 'Other', uncategorized: 'Uncategorized', corporation: 'Corporation',
}

const css = `
.gn {
  --gn-ink: var(--ui-text-primary);
  --gn-muted: var(--ui-text-secondary);
  --gn-rule: var(--ui-stroke-secondary);
  --gn-accent: var(--ui-accent, var(--gn-ink));
  --gn-panel: color-mix(in srgb, var(--gn-ink) 4%, transparent);
  block-size: 100%; min-inline-size: 0; overflow: auto; overscroll-behavior: contain;
  color: var(--gn-ink); font-size: 13px; line-height: 1.5; container-type: inline-size;
}
.gn *, .gn *::before, .gn *::after { box-sizing: border-box; }
.gn-inner { max-inline-size: 880px; margin-inline: auto; padding: clamp(14px, 4cqi, 34px); }
.gn-mini .gn-inner { padding: 13px; }
.gn h1, .gn h2, .gn h3, .gn p, .gn ul, .gn dl { margin: 0; }
.gn h1, .gn h2, .gn h3 { overflow-wrap: anywhere; }
.gn h1, .gn .gn-headline { font-family: Georgia, 'Times New Roman', serif; font-weight: 600; letter-spacing: -.035em; line-height: 1.08; }
.gn h1 { font-size: clamp(30px, 6cqi, 56px); }
.gn .gn-headline { font-size: clamp(26px, 5cqi, 46px); }
.gn-mini h1, .gn-mini .gn-headline { font-size: 23px; }
.gn-header { border-block-start: 3px solid var(--gn-accent); border-block-end: 1px solid var(--gn-rule); padding-block: 13px 16px; margin-block-end: 20px; }
.gn-mini .gn-header { padding-block: 9px 11px; margin-block-end: 13px; }
.gn-mini .gn-pane-search { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px; margin-block-end: 8px; }
.gn-open-story { margin-block-end: 8px; }
.gn-header p { color: var(--gn-muted); margin-block-start: 5px; }
.gn-line { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-inline-size: 0; }
.gn-spread { justify-content: space-between; }
.gn button, .gn input, .gn select {
  border: 1px solid var(--gn-rule); border-radius: 6px; color: var(--gn-ink); background: var(--gn-panel);
  font: inherit; min-block-size: 34px; padding: 5px 9px; min-inline-size: 0;
}
.gn button { cursor: pointer; text-align: start; }
.gn button:disabled { cursor: default; opacity: .65; }
.gn button:hover:not(:disabled), .gn a:hover { background: color-mix(in srgb, var(--gn-accent) 13%, transparent); }
.gn button:focus-visible, .gn a:focus-visible, .gn input:focus-visible, .gn select:focus-visible, .gn [tabindex]:focus-visible {
  outline: 2px solid var(--gn-accent); outline-offset: 2px;
}
.gn .gn-primary { border-color: color-mix(in srgb, var(--gn-accent) 70%, var(--gn-rule)); background: color-mix(in srgb, var(--gn-accent) 16%, transparent); font-weight: 650; }
.gn .gn-quiet { background: transparent; }
.gn input { flex: 1 1 180px; inline-size: 100%; }
.gn input::placeholder { color: var(--gn-muted); }
.gn-kicker, .gn-meta { color: var(--gn-muted); }
.gn-kicker { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; font-weight: 700; }
.gn-meta { font-size: 12px; }
.gn-section { margin-block-start: 19px; }
.gn-section-title { font-size: 15px; font-weight: 700; }
.gn-recent { margin-block-start: 9px; }
.gn-recent button { padding-block: 2px; min-block-size: 28px; max-inline-size: 100%; overflow-wrap: anywhere; }
.gn-list { list-style: none; padding: 0; }
.gn-list > li { border-block-end: 1px solid var(--gn-rule); }
.gn .gn-row { display: block; inline-size: 100%; border: 0; border-radius: 0; background: transparent; padding: 12px 3px; }
.gn-row strong { display: block; font-family: Georgia, 'Times New Roman', serif; font-size: clamp(16px, 2.8cqi, 22px); line-height: 1.22; font-weight: 600; overflow-wrap: anywhere; }
.gn-row .gn-meta { display: block; margin-block-start: 5px; }
.gn-alert { margin-block: 12px; padding: 10px 12px; border: 1px solid var(--gn-rule); border-inline-start: 3px solid var(--gn-accent); background: var(--gn-panel); overflow-wrap: anywhere; }
.gn-description { margin-block-start: 12px !important; max-inline-size: 70ch; white-space: pre-line; overflow-wrap: anywhere; }
.gn-card { border: 1px solid var(--gn-rule); border-radius: 8px; padding: 12px; background: var(--gn-panel); margin-block-start: 12px; }
.gn .gn-coverage {
  --gn-left: color-mix(in srgb, var(--ui-blue, #386ad2) 72%, var(--gn-ink));
  --gn-center: color-mix(in srgb, var(--gn-ink) 60%, var(--gn-rule));
  --gn-right: color-mix(in srgb, var(--ui-red, #ce5147) 76%, var(--gn-ink));
  padding: clamp(12px, 2.4cqi, 20px);
}
.gn .gn-stat-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 3px 12px; }
.gn .gn-spectrum { display: flex; direction: ltr; overflow: hidden; height: 10px; border-radius: 3px; margin-block: 15px 10px; }
.gn .gn-side-mark { background: var(--gn-side); }
.gn .gn-spectrum .gn-side-mark { flex-basis: 0; }
.gn .gn-spectrum .gn-side-mark + .gn-side-mark { box-shadow: inset 2px 0 var(--ui-bg-editor, Canvas); }
.gn .gn-side-left { --gn-side: var(--gn-left); }
.gn .gn-side-center { --gn-side: var(--gn-center); }
.gn .gn-side-right { --gn-side: var(--gn-right); }
.gn .gn-numbers { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-block-start: 9px; }
.gn .gn-numbers > div + div { border-inline-start: 1px solid var(--gn-rule); padding-inline-start: clamp(6px, 2cqi, 18px); }
.gn .gn-numbers dt { display: flex; align-items: center; gap: 5px; color: var(--gn-muted); font-size: 12px; }
.gn .gn-numbers dt::before { content: ''; width: 7px; height: 7px; flex-shrink: 0; border-radius: 2px; background: var(--gn-side); }
.gn .gn-numbers dd { margin: 2px 0 0; line-height: 1.12; font-size: clamp(19px, 3.8cqi, 30px); font-weight: 620; letter-spacing: -.045em; font-variant-numeric: tabular-nums; }
.gn .gn-side-count { display: block; margin-block-start: 2px; letter-spacing: normal; font-weight: 400; }
.gn .gn-coverage .gn-unreported { margin-block-start: 8px; }
.gn .gn-rating-rows { display: grid; margin-block-start: 9px; }
.gn .gn-rating-row { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: baseline; padding-block: 5px; }
.gn .gn-rating-row + .gn-rating-row { border-block-start: 1px solid var(--gn-rule); }
.gn .gn-rating-row dt { font-size: 12px; overflow-wrap: anywhere; z-index: 0; }
.gn .gn-rating-row dd { margin: 0; font-weight: 650; font-variant-numeric: tabular-nums; z-index: 0; }
.gn .gn-rating-row::before { content: ''; position: absolute; inset-block: 3px; inset-inline-start: 0; inline-size: var(--gn-share); border-radius: 2px; background: color-mix(in srgb, var(--gn-ink) 6%, transparent); }
.gn-mini .gn-spectrum { height: 7px; margin-block: 10px 8px; }
.gn-source { padding: 11px 0; overflow-wrap: anywhere; }
.gn a { color: var(--gn-ink); text-decoration: underline; text-underline-offset: 3px; border-radius: 2px; }
.gn-source .gn-meta { display: block; }
.gn-source a { font-weight: 650; }
.gn-detail-top { margin-block: 16px 8px; }
.gn-views { border-block-end: 1px solid var(--gn-rule); padding-block-end: 9px; }
.gn-article-frame { display: block; inline-size: 100%; block-size: clamp(420px, 66vh, 900px); border: 1px solid var(--gn-rule); border-radius: 6px; margin-block-start: 12px; background: white; }
@container (max-width: 355px) {
  .gn-search input { order: -1; flex-basis: 100%; }
  .gn-search select { flex: 1; }
}
`

function readScope() {
  return JSON.stringify([host.state.connectionId.get(), host.state.profile.get()])
}

function subscribeScope(listener) {
  const stopConnection = host.state.connectionId.subscribe(listener)
  const stopProfile = host.state.profile.subscribe(listener)
  return () => { stopConnection(); stopProfile() }
}

function makeReader(ctx) {
  const values = new Map()
  const pending = new Map()
  const listeners = new Set()
  const selections = new Map()
  const pages = new Map()
  const selectionListeners = new Set()
  let revision = 0
  let active = true

  ctx.onDispose(() => { active = false; listeners.clear(); selectionListeners.clear() })
  return {
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    revision: () => revision,
    subscribeSelection(listener) {
      selectionListeners.add(listener)
      return () => selectionListeners.delete(listener)
    },
    select(scope, target) {
      if (target) selections.set(scope, target)
      else selections.delete(scope)
      for (const listener of selectionListeners) listener()
    },
    selection: scope => selections.get(scope) || null,
    page: scope => pages.get(scope),
    rememberPage(scope, page) { pages.set(scope, page) },
    isActive: () => active,
    load(scope, operation, args, refresh = false) {
      const key = JSON.stringify([scope, operation, args])
      const flight = JSON.stringify([key, refresh])
      const local = ['cache', 'snapshot'].includes(operation)
      if (!refresh && !local && values.has(key)) return Promise.resolve(values.get(key))
      if (pending.has(flight)) return pending.get(flight)

      const body = refresh && !local ? { ...args, policy: 'refresh' } : args
      const request = ctx.rest(`/read/${operation}`, { method: 'POST', body, timeoutMs: 59000 })
        .then(result => {
          if (result?.schema_version !== 1 || (!result.data && !result.error)) {
            throw new Error('Hermes returned an unexpected Ground News response.')
          }
          if (!result.error && !local) {
            // A slow normal read must not replace a newer refresh.
            if (refresh || !values.has(key)) values.set(key, result)
            if (values.size > 96) values.delete(values.keys().next().value)
            if (['story', 'lookup', 'feed'].includes(operation)) {
              revision += 1
              for (const listener of listeners) listener()
            }
          }
          return result
        })
        .finally(() => pending.delete(flight))
      pending.set(flight, request)
      return request
    },
  }
}

function useRead(reader, scope, operation, args, revision = 0) {
  const signature = JSON.stringify([scope, operation, args])
  const [state, setState] = useState({ signature, pending: false })
  const [update, setUpdate] = useState(null)
  const refresh = update?.signature === signature && update.revision === revision
  useEffect(() => {
    if (!operation) return
    let current = true
    setState(previous => ({
      signature, pending: true,
      value: previous.signature === signature ? previous.value : undefined,
    }))
    reader.load(scope, operation, args, refresh).then(result => {
      if (!current) return
      setState(previous => ({
        signature, pending: false, error: result.error,
        value: result.error ? previous.value : result,
      }))
    }).catch(error => {
      if (!current) return
      const message = /404|not found/i.test(String(error))
        ? 'Grounded News is unavailable on this Hermes gateway. Check that the plugin is enabled there.'
        : 'Hermes could not reach the Grounded News backend.'
      setState(previous => ({ signature, pending: false, error: { message }, value: previous.value }))
    })
    return () => { current = false }
  }, [reader, signature, revision, update])
  const display = state.signature === signature ? state : { pending: Boolean(operation) }
  return { ...display, refresh: () => setUpdate({ signature, revision }) }
}

function validUrl(raw) {
  if (typeof raw !== 'string' || /[\s\\]/.test(raw)) return null
  try {
    const url = new URL(raw)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}

const STORY_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$/

function storyRequest(input) {
  const value = input.trim()
  if (STORY_ID.test(value)) return { operation: 'story', args: { story_id: value } }
  const url = validUrl(value)
  if (url && url.length <= 2048) return { operation: 'lookup', args: { url } }
  return null
}

function openedStory(result, operation) {
  const data = result.value?.data
  const event = operation === 'story' ? data : operation === 'lookup' ? data?.event : null
  return event?.id ? { id: event.id, event, read: result.value.reads?.at(-1) } : null
}

function textOnly(value) {
  return typeof value === 'string' ? value.replace(/<[^>]*>/g, '').trim() : ''
}

function day(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isFinite(date.getTime())
    ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date) : ''
}

function snapshotLabel(read) {
  return read ? [read.origin === 'network' ? 'Fetched' : 'Saved', day(read.fetched_at)].filter(Boolean).join(' ') : ''
}

function plural(value, unit) {
  return Number.isFinite(value) ? `${value.toLocaleString()} ${unit}${value === 1 ? '' : 's'}` : ''
}

function Button({ children, onClick, main, disabled, type = 'button', ...props }) {
  return h('button', { ...props, type, onClick, disabled, className: main ? 'gn-primary' : 'gn-quiet' }, children)
}

function Link({ ctx, url, children, onOpen }) {
  const href = validUrl(url)
  if (!href) return children
  return h('a', {
    href,
    onClick: async event => {
      event.preventDefault()
      if (onOpen && !(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) {
        onOpen(href)
        return
      }
      if (!(await ctx.os.openExternal(href))) host.notify({ kind: 'error', message: 'Hermes could not open this link.' })
    },
  }, children)
}

function Notices({ state, loading }) {
  return h('div', { 'aria-live': 'polite' },
    state.pending && h('p', { className: 'gn-alert', role: 'status' }, loading),
    state.error && h('p', { className: 'gn-alert', role: 'alert' },
      state.error.message,
      state.error.cached_at ? ' The prior snapshot is still saved.' : ''),
  )
}

function StoryList({ items, onSelect }) {
  return h('ul', { className: 'gn-list' }, items.map((item, index) => h('li', { key: `${item.id}-${index}` },
    h('button', { type: 'button', className: 'gn-row', onClick: () => onSelect(item) },
      h('strong', null, textOnly(item.title || item.name) || item.id),
      h('span', { className: 'gn-meta' },
        [item.type === 'interest' ? textOnly(item.subType) : '',
          plural(item.sourceCount, 'source'), day(item.start), snapshotLabel(item.cache)].filter(Boolean).join(' · ')),
    ),
  )))
}

function Stats({ story, compact = false }) {
  const bias = story.blindspotData || {}
  const counts = [plural(story.sourceCount, 'source'), plural(story.biasSourceCount, 'bias-rated source')].filter(Boolean)
  const sides = SIDES.map(([name, percentKey, countKey]) => {
    const percent = bias[percentKey], count = bias[countKey]
    return {
      name, tone: 'gn-side-' + name.toLowerCase(),
      percent: Number.isFinite(percent) && percent >= 0 && percent <= 100 ? percent : null,
      count: Number.isSafeInteger(count) && count >= 0 ? count : null,
    }
  })
  const hasBias = sides.some(side => side.percent !== null || side.count !== null)
  const total = sides.reduce((sum, side) => sum + (side.percent ?? 0), 0)
  // A complete rounded distribution may add to 99 or 101. Partial figures
  // remain legible in the legend without stretching them into a full bar.
  const usePercents = sides.every(side => side.percent !== null) && Math.abs(100 - total) <= 1
  const useCounts = sides.every(side => side.percent === null && side.count !== null) && sides.some(side => side.count > 0)
  const metric = usePercents ? 'percent' : 'count'
  return h('section', { className: 'gn-card gn-coverage', 'aria-label': 'Ground News coverage statistics' },
    h('div', { className: 'gn-stat-head' },
      h('h3', { className: 'gn-kicker' }, 'Ground News coverage'),
      counts.length > 0 && h('p', { className: 'gn-meta' }, counts.join(' · '))),
    (usePercents || useCounts) && h('div', { className: 'gn-spectrum', 'aria-hidden': true },
      sides.filter(side => side[metric] > 0).map(side =>
        h('span', { key: side.name, className: `gn-side-mark ${side.tone}`, style: { flexGrow: side[metric] } }))),
    hasBias ? h('dl', { className: 'gn-numbers' }, sides.map(side =>
      h('div', { key: side.name, className: side.tone }, h('dt', null, side.name),
        h('dd', null,
          side.percent !== null ? `${side.percent}%` : side.count === null ? h('span', { 'aria-label': 'Not reported' }, '—') : side.count.toLocaleString(),
          side.count !== null && (!compact || side.percent === null) && h('span', { className: 'gn-meta gn-side-count' },
            side.percent === null ? (side.count === 1 ? 'source' : 'sources') : plural(side.count, 'source'))),
      ))) : h('p', { className: 'gn-meta gn-unreported' }, 'Bias breakdown unavailable for this snapshot.'),
  )
}

function Ratings({ title, values }) {
  const entries = Object.entries(values || {}).filter(([, count]) => Number.isSafeInteger(count) && count > 0)
    .sort(([, a], [, b]) => b - a)
  const total = entries.reduce((sum, [, count]) => sum + count, 0)
  return h('section', { className: 'gn-card' },
    h('h3', { className: 'gn-kicker' }, title),
    entries.length === 0 && h('p', { className: 'gn-meta' }, 'No breakdown in this snapshot.'),
    entries.length > 0 && h('dl', { className: 'gn-rating-rows' }, entries.map(([category, count]) =>
      h('div', { className: 'gn-rating-row', key: category, style: { '--gn-share': `${100 * count / total}%` } },
        h('dt', null, RATING_LABELS[category] || category), h('dd', null, count.toLocaleString())))),
  )
}

function originalSource(source) {
  const info = source.sourceInfo || {}
  const href = validUrl(source.url)
  return {
    href, name: textOnly(info.name) || (href ? new URL(href).hostname : 'Unknown publisher'),
    title: textOnly(source.title || source.articleTitle || source.headline),
    bias: BIASES[info.bias] || 'Unrated', date: day(source.date),
  }
}

function publisherArticles(story) {
  const articles = new Map()
  for (const source of Array.isArray(story.sources) ? story.sources : []) {
    if (!source || typeof source !== 'object') continue
    const article = originalSource(source)
    if (article.href && !articles.has(article.href)) articles.set(article.href, article)
  }
  return [...articles.values()]
}

function Publishers({ ctx, articles, compact, onOpen }) {
  const [bias, setBias] = useState('All')
  const types = [...new Set(articles.map(source => source.bias))]
  const filter = types.includes(bias) ? bias : 'All'
  const visible = (filter === 'All' ? articles : articles.filter(source => source.bias === filter))
    .slice(0, compact ? 4 : undefined)

  return h('section', { className: 'gn-section' },
    h('div', { className: 'gn-line gn-spread' },
      h('h3', { className: 'gn-section-title' }, 'Publisher articles'),
      !compact && types.length > 1 && h('select', {
        'aria-label': 'Filter publishers by Ground News bias', value: filter, onChange: event => setBias(event.target.value),
      }, ['All', ...types].map(type => h('option', { key: type, value: type }, type === 'All' ? 'All ratings' : type))),
    ),
    !compact && articles.length > 0 && h('p', { className: 'gn-meta' },
      `${visible.length} of ${articles.length} listed links shown · Ratings by Ground News`),
    !visible.length && h('p', { className: 'gn-alert' }, 'No publisher article links in this snapshot.'),
    h('ul', { className: 'gn-list' }, visible.map(source =>
      h('li', { key: source.href, className: 'gn-source' },
        h(Link, { ctx, url: source.href, onOpen }, source.title || source.name),
        h('span', { className: 'gn-meta' },
          [source.title ? source.name : '', source.bias, source.date].filter(Boolean).join(' · ')),
      ))),
  )
}

function ArticleView({ ctx, articles, index, onOpen, onList, hidden }) {
  const article = articles[index]
  return h('section', { className: 'gn-section', 'aria-label': 'Publisher article', hidden },
    h('div', { className: 'gn-line' },
      h(Button, { onClick: onList }, 'All articles'),
      h(Button, { disabled: index === 0, onClick: () => onOpen(articles[index - 1].href) }, 'Previous'),
      h(Button, { disabled: index === articles.length - 1, onClick: () => onOpen(articles[index + 1].href) }, 'Next'),
      h('span', { className: 'gn-meta' }, `${index + 1} of ${articles.length}`),
    ),
    h('div', { className: 'gn-detail-top', 'aria-live': 'polite' },
      h('h3', { className: 'gn-section-title' }, article.title || article.name),
      h('p', { className: 'gn-meta' }, [article.name, article.bias, article.date].filter(Boolean).join(' · ')),
    ),
    h(Link, { ctx, url: article.href }, 'Open in browser ↗'),
    SandboxedFrame && h(SandboxedFrame, {
      key: article.href, src: article.href, title: `Article from ${article.name}`, className: 'gn-article-frame',
    }),
  )
}

function CoverageViews({ ctx, story, articles, initialArticle }) {
  const [view, setView] = useState(initialArticle ? 'Articles' : 'Overview')
  const [articleUrl, setArticleUrl] = useState(initialArticle)
  const index = articles.findIndex(article => article.href === articleUrl)
  function openArticle(href) {
    setArticleUrl(href)
    setView('Articles')
  }
  return h('div', { className: 'gn-section' },
    h('nav', { className: 'gn-line gn-views', 'aria-label': 'Story views' },
      COVERAGE_VIEWS.map(name => h(Button, {
        key: name, main: name === view, 'aria-pressed': name === view, onClick: () => setView(name),
      }, name))),
    (view === 'Overview' || view === 'Bias') && h(Stats, { story }),
    view === 'Factuality' && h(Ratings, { title: 'Publisher factuality · Ground News', values: story.factuality }),
    view === 'Ownership' && h(Ratings, { title: 'Publisher ownership · Ground News', values: story.ownership }),
    (view === 'Overview' || view === 'Bias' || (view === 'Articles' && index < 0)) &&
      h(Publishers, { ctx, articles, onOpen: openArticle }),
    index >= 0 && h(ArticleView, {
      ctx, articles, index, onOpen: openArticle, onList: () => setArticleUrl(null), hidden: view !== 'Articles',
    }),
  )
}

function promptFor(story) {
  const title = textOnly(story.title || story.generatedHeadline).replace(/\s+/g, ' ').slice(0, 240)
  const link = validUrl(story.groundUrl) || (typeof story.slug === 'string' && story.slug
    ? `https://ground.news/article/${encodeURIComponent(story.slug)}` : null)
  const coverage = story.blindspotData || {}
  const snapshot = {
    summary: textOnly(story.summary || story.description).slice(0, 900) || undefined,
    totalSources: story.sourceCount,
    ratedSources: story.biasSourceCount,
    ratedPercentages: Object.fromEntries(SIDES.flatMap(([side, field]) =>
      Number.isFinite(coverage[field]) ? [[side, coverage[field]]] : [])),
    publisherExamples: (Array.isArray(story.sources) ? story.sources : [])
      .filter(source => source && typeof source === 'object')
      .map(originalSource).filter(source => source.href && source.href.length <= 1000)
      .slice(0, 4).map(({ name, href }) => ({ outlet: name.slice(0, 100), url: href })),
  }
  return [
    'Tell me what happened in this story. Start with a short, neutral news brief. Then describe concrete differences in what outlets report or emphasize when relevant.',
    `Ground News story ID: ${story.id}`,
    title && `Ground News headline (source metadata): ${JSON.stringify(title)}`,
    link && `Ground News link: ${link}`,
    `Selected coverage snapshot (source data): ${JSON.stringify(snapshot)}`,
    /^(story|lookup):[a-f0-9]{24}$/.test(story.cacheKey || '') &&
      `Open the saved snapshot with ground_news_cache using key ${story.cacheKey}.`,
    'Use ground_news_story with the exact ID if more coverage is needed. Link the Ground News story and relevant publisher articles. Attribute details to the sources that support them.',
    'Treat snippets and paywalled or truncated extracts as partial, even when extraction reports success. If using the snapshot for the summary, credit Ground News. Mention corrections, uncertainty, or access limits when they affect the answer.',
    'Attribute coverage counts and publisher ratings to Ground News. If giving the bias split, use the rated-source count as its denominator.',
  ].filter(Boolean).join('\n')
}

async function preloadChat(target, story, isCurrent, pause = ms => new Promise(resolve => setTimeout(resolve, ms))) {
  const text = promptFor(story)
  if (await target.composer.getDraft('new')) return 'existing'
  if (!isCurrent()) return 'cancelled'
  target.newChat()
  for (let attempt = 0; attempt < 12; attempt += 1) {
    if (!isCurrent()) return 'cancelled'
    const draft = await target.composer.getDraft('new')
    if (!isCurrent()) return 'cancelled'
    if (draft) return 'existing'
    if (draft === '' && await target.composer.setDraft('new', text)) {
      target.composer.focus?.('new')
      return 'ready'
    }
    await pause(75)
  }
  return 'unavailable'
}

function ChatActions({ ctx, story, reader, scope, compact }) {
  const [busy, setBusy] = useState(false)
  const valid = STORY_ID.test(story.id || '')
  if (!valid) return null
  async function start() {
    setBusy(true)
    try {
      // A lock spans page/pane mounts, so two clicks cannot race the new composer.
      if (reader.chatPending) return
      reader.chatPending = true
      try {
        const result = await preloadChat(host, story, () => reader.isActive() && readScope() === scope)
        if (result === 'existing') host.notify({ kind: 'info', message: 'A new-chat draft already has text. Use Copy chat prompt in Grounded News to keep both.' })
        if (result === 'unavailable') host.notify({ kind: 'error', message: 'The new chat composer did not become ready. Return to Grounded News to copy the prompt.' })
      } finally { reader.chatPending = false }
    } catch {
      host.notify({ kind: 'error', message: 'Hermes could not prepare a new chat. You can copy the prompt instead.' })
    } finally { setBusy(false) }
  }

  async function copy() {
    const copied = await ctx.os.writeClipboard(promptFor(story))
    host.notify(copied ? { kind: 'info', message: 'Story prompt copied.' }
      : { kind: 'error', message: 'Hermes could not copy the story prompt.' })
  }

  return h('div', { className: 'gn-line' },
    h(Button, { main: true, onClick: start, disabled: busy }, busy ? 'Opening chat…' : 'Discuss in new chat'),
    !compact && h(Button, { onClick: copy }, 'Copy chat prompt'),
  )
}

function Coverage({ ctx, reader, scope, target, compact = false, onBack, backLabel }) {
  const [options, setOptions] = useState(null)
  const heading = useRef(null)
  const operation = options ? 'story' : target.cache ? 'snapshot' : target.event ? null : 'story'
  const args = options || (target.cache ? { key: target.cache.key } : { story_id: target.id })
  const result = useRead(reader, scope, operation, args)
  const [lastStory, setLastStory] = useState(null)
  const currentStory = result.value?.data
  const currentRead = currentStory?.expandedCoverage ? result.value?.reads?.at(-1) : result.value?.reads?.[0]
  useEffect(() => {
    if (currentStory) setLastStory({ story: currentStory, read: currentRead })
  }, [result.value])
  useEffect(() => { heading.current?.focus() }, [])
  const original = currentStory || lastStory?.story || target.event || target
  const story = original.expandedCoverage || original
  const lastRead = currentRead || lastStory?.read || target.read || target.cache
  const expansionError = original.expansionError
  const articles = publisherArticles(story)

  return h('article', { className: 'gn-section' },
    h('div', { className: 'gn-line gn-spread' },
      h(Button, { onClick: onBack }, backLabel || (compact ? '← Saved stories' : '← Results')),
      h('span', { className: 'gn-meta' }, [day(story.start), snapshotLabel(lastRead)].filter(Boolean).join(' · ')),
    ),
    h('div', { className: 'gn-detail-top' },
      h('h2', { className: 'gn-headline', tabIndex: -1, ref: heading }, textOnly(story.title || story.generatedHeadline) || story.id || 'Story coverage'),
      !compact && textOnly(story.generatedHeadline) && textOnly(story.title) &&
        textOnly(story.generatedHeadline) !== textOnly(story.title) &&
        h('p', { className: 'gn-description' }, 'Ground News generated headline · ', textOnly(story.generatedHeadline)),
      !compact && story.description && h('p', { className: 'gn-description' }, textOnly(story.description)),
    ),
    h(Notices, { state: result, loading: options?.more_sources ? 'Checking for more publisher coverage…' : 'Opening story…' }),
    expansionError && h('p', { className: 'gn-alert', role: 'status' }, `More coverage unavailable. ${expansionError.message}`),
    compact && h(Stats, { story, compact: true }),
    h('div', { className: 'gn-line gn-section' },
      h(ChatActions, { ctx, reader, scope, story: { ...story, cacheKey: lastRead?.key }, compact }),
      validUrl(story.groundUrl) && h(Link, { ctx, url: story.groundUrl }, 'Open on Ground News ↗'),
      compact && h(Button, { onClick: () => { reader.select(scope, target); host.navigate(PATH) } }, 'Compare coverage'),
      !compact && h(Button, {
        disabled: result.pending || !story.id,
        onClick: () => {
          if (operation === 'story') result.refresh()
          else setOptions({ story_id: story.id, policy: 'refresh' })
        },
      }, 'Refresh coverage'),
      !compact && !original.expandedCoverage && h(Button, {
        disabled: result.pending || !story.id,
        onClick: () => {
          if (options?.more_sources) result.refresh()
          else setOptions({ story_id: story.id, more_sources: true, sources_limit: 60 })
        },
      }, 'More publishers'),
    ),
    compact
      ? h(Publishers, { ctx, articles, compact: true, onOpen: articleUrl => {
        reader.select(scope, { id: story.id, event: story, read: lastRead, articleUrl })
        host.navigate(PATH)
      } })
      : h(CoverageViews, { ctx, story, articles, initialArticle: target.articleUrl }),
  )
}

const START = { operation: 'cache', args: {}, title: 'Saved stories' }

function useLibraryRevision(reader) {
  return useSyncExternalStore(reader.subscribe, reader.revision)
}

function OpenStoryForm({ onOpen, compact }) {
  const [value, setValue] = useState('')
  const [invalid, setInvalid] = useState(false)
  return h('form', {
    className: compact ? 'gn-pane-search' : 'gn-line gn-search gn-open-story',
    'aria-label': 'Open a story',
    onSubmit: event => {
      event.preventDefault()
      const request = storyRequest(value)
      setInvalid(!request)
      if (request) onOpen({ ...request, title: 'Open story' })
    },
  },
  h('input', {
    type: 'text', value, required: true, maxLength: 2048, autoCapitalize: 'none', spellCheck: false,
    placeholder: 'Story link or ID', 'aria-label': 'Story link or ID', 'aria-invalid': invalid || undefined,
    onChange: event => { setValue(event.target.value); setInvalid(false) },
  }),
  h(Button, { main: true, type: 'submit', disabled: !value.trim() }, 'Open story'),
  invalid && h('p', { className: 'gn-alert', role: 'alert', style: { gridColumn: '1 / -1' } },
    'Paste a Ground News link, a publisher article link, or a Ground News story ID.'),
  )
}

function MiniPane({ ctx, reader, scope }) {
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [request, setRequest] = useState(null)
  const listRef = useRef(null)
  const revision = useLibraryRevision(reader)
  const operation = request?.operation || 'cache'
  const result = useRead(reader, scope, operation, request?.args || { limit: 8 }, request ? 0 : revision)
  const data = result.value?.data
  const direct = operation === 'story' || operation === 'lookup'
  const target = selected || openedStory(result, operation)
  const items = operation === 'search' ? data?.searchResults : data?.entries
  const resultTitle = operation === 'search' ? `Results for “${request.args.query}”`
    : direct ? 'Open story' : 'Saved stories'

  function submit(next) {
    if (request?.operation === next.operation && JSON.stringify(request.args) === JSON.stringify(next.args)) {
      if (result.error) result.refresh()
      return
    }
    setRequest(next)
  }

  return h(Surface, { compact: true },
    h(Header, { compact: true }),
    !target && h('form', {
      className: 'gn-pane-search', role: 'search', 'aria-label': 'Find news stories',
      onSubmit: event => {
        event.preventDefault()
        const value = query.trim()
        if (value) submit({ operation: 'search', args: { kind: 'story', query: value } })
      },
    },
    h('input', {
      type: 'search', value: query, required: true, maxLength: 200,
      placeholder: 'Search headlines', 'aria-label': 'Search story headlines',
      onChange: event => setQuery(event.target.value),
    }),
    h(Button, { main: true, type: 'submit', disabled: !query.trim() }, 'Search news'),
    ),
    !target && h(OpenStoryForm, { onOpen: submit, compact: true }),
    h('div', { className: 'gn-line gn-spread' },
      h(Button, { onClick: () => { reader.select(scope, target); host.navigate(PATH) } }, 'Open full reader'),
      request ? h(Button, { onClick: () => { setSelected(null); setRequest(null) } }, 'Saved stories')
        : !target && h(Button, { onClick: result.refresh, disabled: result.pending }, 'Reload saved'),
    ),
    target ? h(Coverage, {
      key: target.cache?.key || target.id, ctx, reader, scope, target, compact: true,
      backLabel: operation === 'search' ? '← Search results' : '← Saved stories',
      onBack: () => {
        setSelected(null)
        if (direct) setRequest(null)
        requestAnimationFrame(() => listRef.current?.focus())
      },
    }) : h('section', { className: 'gn-section' },
      h('h2', { className: 'gn-section-title', tabIndex: -1, ref: listRef }, resultTitle),
      h(Notices, {
        state: result, loading: operation === 'search' ? 'Searching Ground News…'
          : direct ? 'Opening story…' : 'Reading saved stories…',
      }),
      items?.length > 0 && h(StoryList, { items, onSelect: setSelected }),
      data && !result.pending && !result.error && !items?.length &&
        h('p', { className: 'gn-alert', role: 'status' }, operation === 'search'
          ? 'No stories matched. Try a different headline or topic.'
          : direct ? 'No Ground News match for this article. Try searching for its headline.' : 'Opened stories will appear here.'),
    ),
  )
}

function Header({ compact }) {
  return h('header', { className: 'gn-header' },
    h('h1', null, 'Grounded News'),
    !compact && h('p', null, 'Search Ground News and compare how publishers cover the same story.'),
  )
}

function Surface({ compact, children }) {
  return h('div', { className: compact ? 'gn gn-mini' : 'gn' },
    h('style', null, css), h('div', { className: 'gn-inner' }, children))
}

function feedItems(data) {
  const summaries = new Map((data?.stories || []).map(item => [item.requestedStoryId || item.id, item]))
  return (data?.events?.eventIds || []).map(id => summaries.get(id) || { id })
}

function ResultList({ request, result, onStory, onFeed }) {
  const data = result.value?.data
  const interests = request.operation === 'search' && request.args.kind === 'interest'
  const items = request.operation === 'cache' ? data?.entries
    : request.operation === 'feed' ? feedItems(data)
      : data?.searchResults
  if (request.operation === 'lookup') {
    return data && !result.pending && !result.error &&
      h('p', { className: 'gn-alert', role: 'status' }, 'No Ground News match for this article. Try searching for its headline.')
  }
  if (!items?.length) {
    if (!data || result.pending || result.error) return null
    return h('p', { className: 'gn-alert' },
      request.operation === 'cache' ? 'No saved stories match. Open a story from search to build your library.'
        : 'Ground News returned no results. Try a different search.')
  }
  return h(StoryList, { items, onSelect: interests ? onFeed : onStory })
}

function NewsPage({ ctx, reader, scope }) {
  const [mode, setMode] = useState('story')
  const [query, setQuery] = useState('')
  const [request, setRequest] = useState(() => reader.page(scope)?.request || START)
  const [recent, setRecent] = useState(() => reader.page(scope)?.recent || [])
  const selected = useSyncExternalStore(reader.subscribeSelection, () => reader.selection(scope))
  const heading = useRef(null)
  const version = useLibraryRevision(reader)
  const result = useRead(reader, scope, request.operation, request.args, request.operation === 'cache' ? version : 0)
  const direct = request.operation === 'story' || request.operation === 'lookup'
  const target = selected || openedStory(result, request.operation)
  const inputLabel = {
    story: 'Search story headlines', interest: 'Search topics, publishers, or places',
    cache: 'Search saved stories',
  }[mode]
  useEffect(() => { reader.rememberPage(scope, { request, recent }) }, [reader, scope, request, recent])

  function select(next, remember = false) {
    reader.select(scope, null)
    setRequest(next)
    if (remember) {
      const key = JSON.stringify([next.operation, next.args])
      setRecent(previous => [
        { key, request: next },
        ...previous.filter(previous => previous.key !== key),
      ].slice(0, 6))
    }
  }

  function submit(event) {
    event.preventDefault()
    const value = query.trim()
    if (!value) return
    if (mode === 'cache') select({ operation: 'cache', args: { query: value }, title: 'Saved stories' })
    else select({
      operation: 'search', args: { kind: mode, query: value },
      title: value, label: mode === 'interest' ? `Topics · ${value}` : value,
    }, true)
  }

  function openFeed(item) {
    select({
      operation: 'feed', args: { interest_id: item.id }, title: textOnly(item.name || item.title) || item.id,
    }, true)
  }

  function showSaved() {
    setMode('cache')
    setQuery('')
    reader.select(scope, null)
    select(START)
  }

  return h(Surface, null,
    h(Header, {}),
    h(OpenStoryForm, { onOpen: next => {
      if (request.operation === next.operation && JSON.stringify(request.args) === JSON.stringify(next.args)) {
        reader.select(scope, null)
        if (result.error) result.refresh()
      } else select(next)
    } }),
    h('form', { className: 'gn-line gn-search', role: 'search', onSubmit: submit },
      h('select', {
        value: mode, 'aria-label': 'Search type', onChange: event => { setMode(event.target.value); setQuery('') },
      },
      h('option', { value: 'story' }, 'Stories'),
      h('option', { value: 'interest' }, 'Topics & publishers'),
      h('option', { value: 'cache' }, 'Saved stories')),
      h('input', {
        value: query, onChange: event => setQuery(event.target.value), placeholder: inputLabel,
        'aria-label': inputLabel, maxLength: 200, type: 'search', required: true,
      }),
      h(Button, { main: true, type: 'submit' }, 'Search'),
      h(Button, { onClick: showSaved }, 'Saved stories'),
    ),
    recent.length > 0 && h('nav', { className: 'gn-line gn-recent', 'aria-label': 'Recent topics and searches' },
      h('span', { className: 'gn-meta' }, 'Recent'),
      recent.map(item => h(Button, {
        key: item.key,
        'aria-pressed': request === item.request,
        onClick: () => select(item.request),
      }, item.request.label || item.request.title)),
    ),
    target && h(Coverage, {
      key: JSON.stringify([target.cache?.key || target.id, target.articleUrl]), ctx, reader, scope, target,
      backLabel: direct ? '← Saved stories' : undefined,
      onBack: () => {
        if (direct) select(START)
        else reader.select(scope, null)
        requestAnimationFrame(() => heading.current?.focus())
      },
    }),
    !target && h('section', { className: 'gn-section' },
      h('div', { className: 'gn-line gn-spread' },
        h('h2', { className: 'gn-section-title', tabIndex: -1, ref: heading }, request.title),
        h(Button, { disabled: result.pending, onClick: result.refresh },
          request.operation === 'cache' ? 'Reload saved' : direct ? 'Retry' : 'Refresh results'),
      ),
      result.value?.reads?.[0] && h('p', { className: 'gn-meta' }, snapshotLabel(result.value.reads[0])),
      h(Notices, {
        state: result, loading: request.operation === 'cache' ? 'Reading saved stories…'
          : direct ? 'Opening story…' : 'Checking Ground News…',
      }),
      h(ResultList, { request, result, onStory: story => reader.select(scope, story), onFeed: openFeed }),
    ),
  )
}

function View({ ctx, reader, mini }) {
  const scope = useSyncExternalStore(subscribeScope, readScope)
  return h(mini ? MiniPane : NewsPage, { key: scope, ctx, reader, scope })
}

export { makeReader, preloadChat, promptFor, storyRequest, validUrl }

export default {
  id: 'grounded-hermes',
  name: 'Grounded News',
  register(ctx) {
    const reader = makeReader(ctx)
    ctx.registerMany([
      {
        id: 'mini', area: 'panes', title: 'Grounded News',
        data: { placement: 'right', width: '292px' },
        render: () => h(View, { ctx, reader, mini: true }),
      },
      {
        id: 'page', area: ROUTES_AREA, data: { path: PATH },
        render: () => h(View, { ctx, reader, mini: false }),
      },
      {
        id: 'nav', area: SIDEBAR_NAV_AREA,
        data: { path: PATH, label: 'Grounded News', codicon: 'book' },
      },
    ])
  },
}
