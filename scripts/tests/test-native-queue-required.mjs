import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';

// Exercise the exact trusted workflow code without checking out PR code.
const workflow = readFileSync(new URL('../../.github/workflows/native-queue-required.yml', import.meta.url), 'utf8');
const code = workflow.split('          script: |\n')[1].split('\n').map(line => line.slice(12)).join('\n');
const execute = new (Object.getPrototypeOf(async function () {}).constructor)('github', 'context', 'core', code);
function fixture(branch = 'main') {
  const repository = {nameWithOwner: 'rckt-corp/example', defaultBranchRef: {name: branch},
    mergeQueue: {configuration: {mergingStrategy: 'ALLGREEN', mergeMethod: 'SQUASH'}}};
  const context = {repo: {owner: 'rckt-corp', repo: 'example'}, eventName: 'pull_request',
    payload: {pull_request: {base: {ref: branch, repo: {full_name: 'rckt-corp/example'}}},
      merge_group: {base_ref: `refs/heads/${branch}`}}};
  const state = {repository, calls: []};
  const github = {graphql: async (query, variables) => {
    assert(!query.includes('mutation'), 'Gate must remain read-only');
    state.calls.push(variables);
    return {repository: state.repository};
  }};
  return {state, context, github, run: () => execute(github, context, {info() {}})};
}
test('configured queues pass PR and merge-group gates without requiring queue entries', async () => {
  const f = fixture(); await f.run();
  f.context.eventName = 'merge_group'; await f.run();
  assert.deepEqual(f.state.calls, [{owner: 'rckt-corp', repo: 'example', branch: 'main'},
    {owner: 'rckt-corp', repo: 'example', branch: 'main'}]);
});
test('default branches are queried from event data without hardcoding main', async () => {
  const f = fixture('release/current'); await f.run();
  f.context.eventName = 'merge_group'; await f.run();
  assert(f.state.calls.every(call => call.branch === 'release/current'));
});
test('new repositories without a native queue and incompatible configurations fail closed', async () => {
  for (const mutate of [f => f.state.repository.mergeQueue = null,
    f => f.state.repository.mergeQueue = {},
    f => f.state.repository.mergeQueue.configuration.mergingStrategy = 'HEADGREEN',
    f => f.state.repository.mergeQueue.configuration.mergeMethod = 'MERGE',
    f => f.state.repository.mergeQueue.configuration.mergeMethod = 'REBASE']) {
    const f = fixture(); mutate(f); await assert.rejects(f.run, /ALLGREEN\/SQUASH/);
  }
});
test('incomplete repository/default-branch API responses cannot authorize merging', async () => {
  for (const mutate of [f => f.state.repository = null,
    f => f.state.repository.defaultBranchRef = null,
    f => f.state.repository.defaultBranchRef.name = 'other',
    f => f.state.repository.nameWithOwner = 'rckt-corp/other']) {
    const f = fixture(); mutate(f); await assert.rejects(f.run, /default branch/);
  }
});
test('wrong event, missing branch, foreign organization or foreign PR base cannot pass', async () => {
  for (const mutate of [f => f.context.eventName = 'push',
    f => f.context.payload.pull_request.base.ref = '',
    f => f.context.payload.pull_request.base.repo.full_name = 'other/repo',
    f => f.context.repo.owner = 'other',
    f => {f.context.eventName = 'merge_group'; f.context.payload.merge_group.base_ref = 'refs/tags/main';}]) {
    const f = fixture(); mutate(f); await assert.rejects(f.run); assert.equal(f.state.calls.length, 0);
  }
});
test('API denial cannot produce a successful policy check', async () => {
  const f = fixture(); f.github.graphql = async () => {throw new Error('API denied');};
  await assert.rejects(f.run, /API denied/);
});

test('public source remains a pinned read-only workflow with cross-repository injection enabled', () => {
  assert.match(workflow, /on:\n  pull_request:\n  merge_group:/);
  assert.match(workflow, /    if: true/);
  assert.match(workflow, /permissions:\n  contents: read\n  pull-requests: read/);
  assert.match(workflow, /actions\/github-script@[a-f0-9]{40}/);
  assert(!workflow.includes('actions/checkout'));
  assert(!workflow.includes('secrets.'));
  assert(!workflow.includes(': write'));
});

test('public consumers use hosted isolation and private consumers use ARC for both events', () => {
  const expression = workflow.match(/    runs-on: \$\{\{ (.+) \}\}/)?.[1];
  assert.equal(expression, "github.event.repository.private && 'rckt-arc-lite' || 'ubuntu-latest'");
  const route = new Function('github', `return (${expression});`);
  for (const eventName of ['pull_request', 'merge_group']) {
    for (const isPrivate of [false, undefined]) {
      const event = {repository: {private: isPrivate},
        pull_request: {head: {repo: {private: true}}}};
      assert.equal(route({event, event_name: eventName}), 'ubuntu-latest');
    }
    assert.equal(route({event: {repository: {private: true}}, event_name: eventName}), 'rckt-arc-lite');
  }
});
