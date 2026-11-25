import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { SourceTextModule, SyntheticModule } from 'node:vm'

const source = await readFile(new URL('../../desktop/plugin.js', import.meta.url), 'utf8')
const module = new SourceTextModule(source)
await module.link(specifier => {
  if (specifier === '@hermes/plugin-sdk') {
    return new SyntheticModule(['host', 'ROUTES_AREA', 'SIDEBAR_NAV_AREA'], function () {
      this.setExport('host', {})
      this.setExport('ROUTES_AREA', 'routes')
      this.setExport('SIDEBAR_NAV_AREA', 'sidebar.nav')
    })
  }
  assert.equal(specifier, 'react')
  return new SyntheticModule(['createElement', 'useEffect', 'useRef', 'useState', 'useSyncExternalStore'], function () {
    this.setExport('createElement', (component, props) => ({ component, props }))
  })
})
await module.evaluate()
const { default: plugin, makeReader, preloadChat, promptFor, storyRequest, validUrl } = module.namespace

const story = {
  id: 'budget_01', title: 'Budget <b>talks</b> resume',
  groundUrl: 'https://ground.news/article/budget-talks',
}
const noDelay = async () => {}
const envelope = data => ({ schema_version: 1, data, reads: [] })

test('registers the native pane and workspace route under the shared plugin ID', () => {
  const contributions = []
  plugin.register({
    onDispose() {},
    registerMany(items) { contributions.push(...items) },
  })
  assert.equal(plugin.id, 'grounded-hermes')
  assert.deepEqual(contributions.map(({ area }) => area), ['panes', 'routes', 'sidebar.nav'])
  assert.equal(contributions[0].render().props.mini, true)
  assert.equal(contributions[1].data.path, contributions[2].data.path)
  assert.equal(contributions[1].render().props.mini, false)
})

test('preloads the identified story only after the new composer mounts', async () => {
  const drafts = [null, null, '', '']
  const writes = []
  const host = {
    newChat: () => writes.push('newChat'),
    composer: {
      getDraft: async id => { assert.equal(id, 'new'); return drafts.shift() },
      setDraft: async (id, text) => {
        assert.equal(id, 'new')
        writes.push(text)
        return writes.length === 3
      },
    },
  }
  assert.equal(await preloadChat(host, story, () => true, noDelay), 'ready')
  assert.deepEqual(writes, ['newChat', promptFor(story), promptFor(story)])
  assert.match(writes[1], /^Tell me what happened in this story\. Start with a short, neutral news brief\./)
  assert.match(writes[1], /Ground News story ID: budget_01/)
  assert.match(writes[1], /Budget talks resume/)
})

test('preserves both an existing draft and a draft typed while the chat mounts', async () => {
  for (const drafts of [['Unsent message'], [null, null, 'New typing']]) {
    let navigations = 0
    const alreadyHadDraft = drafts.length === 1
    const host = {
      newChat: () => { navigations += 1 },
      composer: {
        getDraft: async () => drafts.shift(),
        setDraft: async () => assert.fail('existing draft would be overwritten'),
      },
    }
    assert.equal(await preloadChat(host, story, () => true, noDelay), 'existing')
    assert.equal(navigations, alreadyHadDraft ? 0 : 1)
  }
})

test('fails closed if the scope changes or if the new composer cannot be read', async () => {
  let current = true
  const host = {
    newChat: () => { current = false },
    composer: {
      getDraft: async () => null,
      setDraft: async () => assert.fail('composer must be mounted and empty'),
    },
  }
  assert.equal(await preloadChat(host, story, () => current, noDelay), 'cancelled')
  assert.equal(await preloadChat(host, story, () => true, noDelay), 'unavailable')
})

test('memoizes topic reads per scope and refreshes only on request', async () => {
  const calls = []
  const reader = makeReader({
    onDispose() {},
    rest: async (path, opts) => { calls.push([path, opts.body]); return envelope({ call: calls.length }) },
  })
  const a = { query: 'budget', kind: 'story' }
  const b = { query: 'space', kind: 'story' }
  const first = reader.load('profile-a', 'search', a)
  assert.equal(reader.load('profile-a', 'search', a), first)
  assert.equal((await first).data.call, 1)
  await reader.load('profile-a', 'search', b)
  assert.equal((await reader.load('profile-a', 'search', a)).data.call, 1)
  assert.equal((await reader.load('profile-a', 'search', a, true)).data.call, 3)
  assert.equal((await reader.load('profile-a', 'search', a)).data.call, 3)
  assert.equal((await reader.load('profile-b', 'search', a)).data.call, 4)
  await reader.load('profile-a', 'cache', {}, true)
  assert.deepEqual(calls, [
    ['/read/search', a], ['/read/search', b], ['/read/search', { ...a, policy: 'refresh' }],
    ['/read/search', a], ['/read/cache', {}],
  ])
})

test('ignores an older topic response that resolves after a refresh', async () => {
  const resolve = []
  const reader = makeReader({
    onDispose() {},
    rest: () => new Promise(done => resolve.push(done)),
  })
  const args = { query: 'budget' }
  const normal = reader.load('profile-a', 'search', args)
  const fresh = reader.load('profile-a', 'search', args, true)
  resolve[1](envelope({ version: 'fresh' }))
  await fresh
  resolve[0](envelope({ version: 'old' }))
  await normal
  assert.equal((await reader.load('profile-a', 'search', args)).data.version, 'fresh')
})

test('external article links accept HTTP(S) and reject other schemes or credentials', () => {
  assert.equal(validUrl(story.groundUrl), story.groundUrl)
  for (const url of ['javascript:alert(1)', 'file:///tmp/story', 'https://a:b@example.com/', 'https://example.com/\n']) {
    assert.equal(validUrl(url), null)
  }
})

test('opens exact story IDs and article links through the existing gateway reads', () => {
  assert.deepEqual(storyRequest(' budget_01 '), { operation: 'story', args: { story_id: 'budget_01' } })
  for (const url of [story.groundUrl, 'https://publisher.example/article?ref=share']) {
    assert.deepEqual(storyRequest(url), { operation: 'lookup', args: { url } })
  }
  for (const value of ['a whole headline', 'javascript:alert(1)', 'https://a:b@example.com/', '']) {
    assert.equal(storyRequest(value), null)
  }
})

test('shares the paywall preference across reader views and restores it from Desktop storage', () => {
  const values = new Map()
  const ctx = { onDispose() {}, storage: values }
  const reader = makeReader(ctx)
  const seen = []
  const unsubscribe = reader.subscribePaywalls(() => seen.push(reader.hidePaywalled()))
  assert.equal(reader.hidePaywalled(), false)
  reader.togglePaywalls()
  assert.deepEqual(seen, [true])
  assert.equal(makeReader(ctx).hidePaywalled(), true)
  unsubscribe()
  reader.togglePaywalls()
  assert.deepEqual(seen, [true])
  assert.equal(makeReader(ctx).hidePaywalled(), false)
})
