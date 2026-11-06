import { listFrom } from './models';

describe('listFrom', () => {
  it('returns arrays unchanged', () => {
    const records = [{ id: '1' }];
    expect(listFrom(records)).toBe(records);
  });

  it('supports common API list envelopes', () => {
    expect(listFrom({ items: [1, 2] })).toEqual([1, 2]);
    expect(listFrom({ results: [3] })).toEqual([3]);
    expect(listFrom({ data: [4] })).toEqual([4]);
  });

  it('returns an empty list for empty or missing responses', () => {
    expect(listFrom(null)).toEqual([]);
    expect(listFrom(undefined)).toEqual([]);
    expect(listFrom({})).toEqual([]);
  });
});
