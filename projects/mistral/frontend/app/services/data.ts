export const PP_TIME_RANGES = [
  { code: -1, desc: "-" },
  { code: 0, desc: "Average" },
  { code: 1, desc: "Accumulation" },
  { code: 2, desc: "Maximum" },
  { code: 3, desc: "Minimum" },
  { code: 4, desc: "Difference" },
  { code: 6, desc: "Standard deviation" },
  { code: 254, desc: "Immediate" },
];

/**
 * Return description for a given code in an array of values.
 * @param code
 * @param values
 */
export function decode(code, values) {
  let t = values.find((x) => x.code === code);
  return t !== undefined ? t.desc : code;
}
