import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildDigest} from '../web/engine.js';

const fixtures = JSON.parse(readFileSync(new URL('./generated-parity.json', import.meta.url), 'utf8'));
assert.ok(fixtures.length > 200, 'Regenerate the Python parity matrix');
for(const fixture of fixtures) {
  test(fixture.name, ()=>{
    const input=structuredClone(fixture.input), before=structuredClone(input);
    if(fixture.valid) assert.deepStrictEqual(buildDigest(input),fixture.expected);
    else assert.throws(()=>buildDigest(input));
    assert.deepStrictEqual(input,before,'Engine must not alter sources');
  });
}
